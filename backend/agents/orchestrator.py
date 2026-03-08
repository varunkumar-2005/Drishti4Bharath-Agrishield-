"""
AgentOrchestrator — coordinates the 5-agent AgroShield pipeline:
  Agent 1 → EventCollector
  Agent 2 → EventProcessor
  Agent 3 → RiskPredictor
  Agent 4 → ImpactReasoner
  Agent 5 → AdvisoryGenerator
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from agents.event_collector import EventCollector
from agents.event_processor import EventProcessor
from agents.risk_predictor import RiskPredictor
from agents.impact_reasoner import ImpactReasoner
from agents.advisory_generator import AdvisoryGenerator
from utils.data_loader import DataLoader
from utils.store import InMemoryStore

logger = logging.getLogger("agroshield.orchestrator")
DROP_LOW_RISK_EVENTS = os.getenv("DROP_LOW_RISK_EVENTS", "true").lower() == "true"


class AgentOrchestrator:
    def __init__(self, data_loader: DataLoader, store: InMemoryStore):
        self.data_loader = data_loader
        self.store = store

        self.collector = EventCollector()
        self.processor = EventProcessor()
        self.predictor = RiskPredictor()
        self.reasoner = ImpactReasoner()
        self.advisor = AdvisoryGenerator()

    async def run_pipeline(self):
        """Full pipeline: fetch → process → predict → advise → store."""
        logger.info("Pipeline run starting …")

        # Agent 1: fetch raw events from GDELT
        raw_articles = await self.collector.fetch_events()
        logger.info("Agent1: fetched %d raw articles", len(raw_articles))

        new_events = 0
        for article in raw_articles:
            event_id = article.get("event_id", "")
            if self.store.is_seen(event_id):
                continue

            # Filter for agri relevance
            if not self.collector.is_agri_relevant(article.get("title", "")):
                continue

            await self._process_article(article)
            new_events += 1

            # Avoid rate-limiting Bedrock
            await asyncio.sleep(0.5)

        logger.info("Pipeline run complete: %d new events processed", new_events)

    async def analyze_headline(self, headline: str, url: Optional[str] = None):
        """Manual analysis of a custom headline (POST /api/analyze)."""
        import hashlib, datetime
        article = {
            "event_id": hashlib.md5(headline.encode()).hexdigest()[:16],
            "title": headline,
            "url": url or "",
            "avg_tone": -3.0,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }
        await self._process_article(article, force=True)

    async def _process_article(self, article: Dict[str, Any], force: bool = False):
        """Process a single article through all agents."""
        headline = article.get("title", "")
        try:
            # Agent 2: structure the event
            structured = self.processor.process(article)
            if not structured:
                return

            # Get real country stats from S3 data
            country = structured.get("primary_country", "GLOBAL")
            country_stats = self.data_loader.get_country_stats(country)

            # Agent 3: predict risk level
            prediction = self.predictor.predict(structured, country_stats)

            # Skip very low-risk events unless forced/configured otherwise.
            if (
                DROP_LOW_RISK_EVENTS
                and not force
                and prediction.get("risk_label") == "LOW"
                and prediction.get("risk_score", 0) < 25
            ):
                return

            # Agent 4: derive cascading impact
            impact = self.reasoner.reason(structured, country_stats, prediction, self.data_loader)

            # Build combined event record
            event_record = {
                **structured,
                **prediction,
                **{f"impact_{k}": v for k, v in impact.items()},
                "revenue_at_risk_usd": impact.get("revenue_at_risk_usd", 0),
                "trade_impact_summary": impact.get("trade_impact_summary", ""),
            }
            self.store.add_event(event_record)

            # Agent 5: generate advisory via Bedrock
            advisory = await self.advisor.generate(
                headline=headline,
                structured_event=structured,
                prediction=prediction,
                impact=impact,
                country_stats=country_stats,
            )
            self.store.add_advisory(advisory)

            logger.info(
                "✓ %s | %s | %s | score=%s",
                headline[:60],
                structured.get("primary_country"),
                prediction.get("risk_label"),
                prediction.get("risk_score"),
            )

        except Exception as exc:
            logger.error("Error processing '%s': %s", headline[:60], exc, exc_info=True)
