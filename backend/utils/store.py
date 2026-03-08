"""
InMemoryStore: keeps last N events and advisories in RAM,
also persists to DynamoDB when configured.
"""

import json
import logging
import os
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger("agroshield.store")

MAX_EVENTS = 100
MAX_ADVISORIES = 50
MAX_CHAT_LOGS = 200

DYNAMO_EVENTS_TABLE = os.getenv("DYNAMO_EVENTS_TABLE", "agroshield-events")
DYNAMO_ADVISORIES_TABLE = os.getenv("DYNAMO_ADVISORIES_TABLE", "agroshield-advisories")
DYNAMO_CHAT_TABLE = os.getenv("DYNAMO_CHAT_TABLE", "agroshield-chat-logs")
USE_DYNAMO = os.getenv("USE_DYNAMO", "false").lower() == "true"


class InMemoryStore:
    def __init__(self):
        self._events: deque = deque(maxlen=MAX_EVENTS)
        self._advisories: deque = deque(maxlen=MAX_ADVISORIES)
        self._chat_logs: deque = deque(maxlen=MAX_CHAT_LOGS)
        self._seen_event_ids: set = set()
        self._dynamo = None
        if USE_DYNAMO:
            try:
                import boto3
                self._dynamo = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "ap-south-1"))
                logger.info("DynamoDB connected")
            except Exception as exc:
                logger.warning("DynamoDB init failed: %s", exc)

    # ── Events ─────────────────────────────────────────────────────────────────
    def add_event(self, event: Dict[str, Any]):
        eid = event.get("event_id", "")
        if eid and eid in self._seen_event_ids:
            return False
        if eid:
            self._seen_event_ids.add(eid)
        event["stored_at"] = datetime.utcnow().isoformat() + "Z"
        self._events.appendleft(event)
        self._persist_event(event)
        return True

    def get_events(self, limit: int = 50) -> List[Dict]:
        return list(self._events)[:limit]

    def event_count(self) -> int:
        return len(self._events)

    def is_seen(self, event_id: str) -> bool:
        return event_id in self._seen_event_ids

    # ── Advisories ─────────────────────────────────────────────────────────────
    def add_advisory(self, advisory: Dict[str, Any]):
        advisory["stored_at"] = datetime.utcnow().isoformat() + "Z"
        self._advisories.appendleft(advisory)
        self._persist_advisory(advisory)

    def get_advisories(self, limit: int = 20) -> List[Dict]:
        return list(self._advisories)[:limit]

    def advisory_count(self) -> int:
        return len(self._advisories)

    # —— Chat logs ———————————————————————————————————————————————————————————————
    def add_chat_log(self, chat: Dict[str, Any]):
        if not chat.get("chat_id"):
            chat["chat_id"] = str(uuid.uuid4())
        chat["stored_at"] = datetime.utcnow().isoformat() + "Z"
        self._chat_logs.appendleft(chat)
        self._persist_chat(chat)

    def get_chat_logs(self, limit: int = 50) -> List[Dict]:
        return list(self._chat_logs)[:limit]

    def chat_count(self) -> int:
        return len(self._chat_logs)

    # ── Dashboard KPIs ─────────────────────────────────────────────────────────
    def get_dashboard_kpis(self) -> Dict[str, Any]:
        events = list(self._events)
        advisories = list(self._advisories)

        critical = sum(1 for e in events if e.get("risk_label") == "CRITICAL")
        high = sum(1 for e in events if e.get("risk_label") == "HIGH")
        medium = sum(1 for e in events if e.get("risk_label") == "MEDIUM")
        low = sum(1 for e in events if e.get("risk_label") == "LOW")

        trade_at_risk = sum(e.get("revenue_at_risk_usd", 0) for e in events[:20])
        avg_risk_score = (
            sum(e.get("risk_score", 0) for e in events[:10]) / max(len(events[:10]), 1)
        )

        # Ticker items from top events
        ticker = []
        for e in events[:8]:
            label = e.get("risk_label", "LOW")
            headline = e.get("headline", "")[:80]
            impact = e.get("trade_impact_summary", "")
            if headline:
                ticker.append({"label": label, "text": f"{headline} — {impact}"})

        return {
            "active_threats": len([e for e in events if e.get("risk_label") in ("CRITICAL", "HIGH")]),
            "critical_count": critical,
            "high_count": high,
            "medium_count": medium,
            "low_count": low,
            "trade_at_risk_usd": round(trade_at_risk, 2),
            "advisories_count": len(advisories),
            "avg_risk_score": round(avg_risk_score, 1),
            "top_events": events[:7],
            "latest_advisories": advisories[:3],
            "ticker": ticker,
        }

    # ── DynamoDB persistence ───────────────────────────────────────────────────
    def _persist_event(self, event: Dict):
        if not self._dynamo:
            return
        try:
            table = self._dynamo.Table(DYNAMO_EVENTS_TABLE)
            # DynamoDB requires Decimal for floats — simplify by storing JSON string
            table.put_item(Item={"event_id": event.get("event_id", "unknown"),
                                  "data": json.dumps(event, default=str)})
        except Exception as exc:
            logger.debug("DynamoDB event persist failed: %s", exc)

    def _persist_advisory(self, advisory: Dict):
        if not self._dynamo:
            return
        try:
            table = self._dynamo.Table(DYNAMO_ADVISORIES_TABLE)
            table.put_item(Item={"advisory_id": advisory.get("advisory_id", "unknown"),
                                  "data": json.dumps(advisory, default=str)})
        except Exception as exc:
            logger.debug("DynamoDB advisory persist failed: %s", exc)

    def _persist_chat(self, chat: Dict):
        if not self._dynamo:
            return
        try:
            table = self._dynamo.Table(DYNAMO_CHAT_TABLE)
            table.put_item(Item={"chat_id": chat.get("chat_id", "unknown"),
                                  "data": json.dumps(chat, default=str)})
        except Exception as exc:
            logger.debug("DynamoDB chat persist failed: %s", exc)
