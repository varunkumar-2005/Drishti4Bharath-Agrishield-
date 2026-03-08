"""
Agent 1 — Event Collector
Fetches real-time geopolitical events from GDELT API,
filters for India agricultural trade relevance.
"""

import hashlib
import json
import logging
import os
import re
import csv
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("agroshield.agent1")

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"
EVENT_SOURCE = os.getenv("EVENT_SOURCE", "gdelt").strip().lower()
MOCK_GDELT_FILE = os.getenv("MOCK_GDELT_FILE", "data/agroshield_headlines.csv")
FILE_EVENT_LIMIT = int(os.getenv("FILE_EVENT_LIMIT", "0"))

# Keywords that indicate agricultural trade relevance
AGRI_KEYWORDS = [
    "tariff", "sanction", "embargo", "trade war", "export ban", "import ban",
    "rice", "wheat", "cotton", "spice", "agriculture", "agri", "food",
    "fertilizer", "fertiliser", "crop", "grain", "palm oil", "edible oil",
    "conflict", "war", "blockade", "hormuz", "suez", "shipping", "supply chain",
    "india trade", "india export", "india import", "indian farmer",
    "food security", "commodity", "inflation", "oil price", "fuel",
    "drought", "flood", "climate", "harvest", "msp", "procurement",
]

GDELT_QUERIES = [
    "India agriculture trade tariff sanction",
    "India export import geopolitical conflict",
    "India food grain rice wheat trade disruption",
    "sanctions tariff trade war agriculture 2025",
    "Iran Israel conflict Hormuz shipping",
]


class EventCollector:
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0)

    async def fetch_events(self) -> List[Dict[str, Any]]:
        """
        Fetch and deduplicate events.
        - EVENT_SOURCE=gdelt: real-time GDELT API (default)
        - EVENT_SOURCE=file|mock|local: load from MOCK_GDELT_FILE
        """
        if EVENT_SOURCE in {"file", "mock", "local"}:
            logger.info("Using file-based event source: %s", MOCK_GDELT_FILE)
            return self._fetch_from_file(MOCK_GDELT_FILE)

        # Real-time GDELT path kept intact (do not remove).
        all_articles = []
        for query in GDELT_QUERIES:
            try:
                articles = await self._fetch_gdelt(query)
                all_articles.extend(articles)
            except Exception as exc:
                logger.warning("GDELT query '%s' failed: %s", query, exc)

        # Deduplicate by URL
        seen_urls = set()
        unique = []
        for a in all_articles:
            url = a.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(a)

        logger.info("Fetched %d unique raw articles from GDELT", len(unique))
        return unique

    def _fetch_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(file_path):
            logger.warning("Mock headline file not found: %s", file_path)
            return []

        ext = os.path.splitext(file_path)[1].lower()
        rows: List[Dict[str, Any]] = []

        try:
            if ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, str):
                            rows.append({"title": item})
                        elif isinstance(item, dict):
                            rows.append(item)
            elif ext == ".csv":
                with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    rows = [{"title": line.strip()} for line in f if line.strip()]
        except Exception as exc:
            logger.warning("Failed reading mock headline file %s: %s", file_path, exc)
            return []

        result: List[Dict[str, Any]] = []
        seen_ids = set()
        for raw in rows:
            title = str(raw.get("title") or raw.get("headline") or "").strip()
            if not title:
                continue

            url = str(raw.get("url") or "")
            source_country = str(raw.get("source_country") or raw.get("country") or raw.get("primary_country") or "")
            tone_val = raw.get("avg_tone", raw.get("tone", 0))
            try:
                avg_tone = float(tone_val)
            except Exception:
                avg_tone = 0.0

            ts = str(raw.get("timestamp") or "")
            # In mock/file mode, allow updated headlines with same URL to be treated as new.
            # This prevents stale dedupe when users edit local JSON/CSV test data.
            provided_id = str(raw.get("event_id") or raw.get("id") or "").strip()
            if provided_id:
                event_id = provided_id
            else:
                event_id = self._make_id(f"{url}|{title}|{source_country}|{avg_tone}")
            if event_id in seen_ids:
                continue
            seen_ids.add(event_id)
            result.append({
                "event_id": event_id,
                "title": title,
                "url": url,
                "avg_tone": avg_tone,
                "source_country": source_country,
                "primary_country": str(raw.get("primary_country") or ""),
                "event_type": str(raw.get("event_type") or ""),
                "severity_pct": raw.get("severity_pct"),
                "estimated_goldstein": raw.get("estimated_goldstein"),
                "affected_commodities": str(raw.get("affected_commodities") or ""),
                "affected_states": str(raw.get("affected_states") or ""),
                "risk_label_hint": str(raw.get("risk_label") or ""),
                "seendate": "",
                "timestamp": ts or datetime.utcnow().isoformat() + "Z",
            })

        if FILE_EVENT_LIMIT > 0:
            result = result[:FILE_EVENT_LIMIT]
            logger.info("File event limit active: %d", FILE_EVENT_LIMIT)

        logger.info("Loaded %d unique headlines from %s", len(result), file_path)
        return result

    async def _fetch_gdelt(self, query: str) -> List[Dict[str, Any]]:
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": 25,
            "format": "json",
            "timespan": "1d",
            "sort": "HybridRel",
        }
        resp = await self._client.get(GDELT_API, params=params)
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("articles", [])
        result = []
        for art in articles:
            title = art.get("title", "").strip()
            if not title:
                continue
            tone_raw = art.get("tone", "0,0,0,0,0,0,0")
            avg_tone = self._parse_tone(tone_raw)
            url = art.get("url", "")
            seendate = art.get("seendate", "")
            result.append({
                "event_id": self._make_id(url or title),
                "title": title,
                "url": url,
                "avg_tone": avg_tone,
                "source_country": art.get("sourcecountry", ""),
                "seendate": seendate,
                "timestamp": self._parse_timestamp(seendate),
            })
        return result

    def _parse_tone(self, tone_str: str) -> float:
        try:
            parts = str(tone_str).split(",")
            return float(parts[0])
        except Exception:
            return 0.0

    def _parse_timestamp(self, seendate: str) -> str:
        try:
            dt = datetime.strptime(seendate, "%Y%m%dT%H%M%SZ")
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            return datetime.utcnow().isoformat() + "Z"

    def _make_id(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()[:16]

    def is_agri_relevant(self, title: str) -> bool:
        """Filter: keep only articles relevant to India's agricultural trade."""
        title_lower = title.lower()
        return any(kw in title_lower for kw in AGRI_KEYWORDS)
