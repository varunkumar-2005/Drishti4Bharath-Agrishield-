"""
AgroShield - Geopolitical Agricultural Trade Intelligence System
FastAPI Backend: Multi-agent pipeline + Amazon Bedrock advisory generation
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load backend/.env before importing modules that read env vars at import time.
load_dotenv(Path(__file__).with_name(".env"))

from agents.orchestrator import AgentOrchestrator
from agents.farmer_chat import FarmerChatAssistant
from utils.data_loader import DataLoader
from utils.store import InMemoryStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("agroshield.main")

data_loader: Optional[DataLoader] = None
store = InMemoryStore()
orchestrator: Optional[AgentOrchestrator] = None
farmer_chat: Optional[FarmerChatAssistant] = None
pipeline_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global data_loader, orchestrator, farmer_chat, pipeline_task
    logger.info("AgroShield starting...")

    data_loader = DataLoader()
    await data_loader.load()

    orchestrator = AgentOrchestrator(data_loader=data_loader, store=store)
    farmer_chat = FarmerChatAssistant()

    # Start background pipeline (every 300 s by default)
    pipeline_task = asyncio.create_task(pipeline_loop())
    logger.info("Pipeline started")

    yield

    if pipeline_task:
        pipeline_task.cancel()
    logger.info("AgroShield shutdown")


async def pipeline_loop():
    """Background task: fetch -> process -> predict -> advise."""
    while True:
        try:
            await orchestrator.run_pipeline()
        except Exception as exc:
            logger.error("Pipeline error: %s", exc, exc_info=True)
        await asyncio.sleep(int(os.getenv("PIPELINE_INTERVAL_SECONDS", "300")))


app = FastAPI(
    title="AgroShield API",
    version="1.0.0",
    description="Geopolitical Agricultural Trade Intelligence for India",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    headline: str
    source_url: Optional[str] = None


class FarmerChatRequest(BaseModel):
    question: str
    state: Optional[str] = None
    crop: Optional[str] = None
    season: Optional[str] = None


def _label_to_score(label: str) -> int:
    mapping = {"LOW": 20, "MEDIUM": 45, "HIGH": 70, "CRITICAL": 90}
    return mapping.get(str(label or "").upper(), 35)


def _build_crop_risk_context(events: List[Dict[str, Any]], query_crop: Optional[str]) -> Dict[str, Any]:
    crop_stats: Dict[str, Dict[str, Any]] = {}
    for event in events:
        commodities = []
        commodities.extend(event.get("affected_commodities") or [])
        commodities.extend(event.get("impact_affected_commodities") or [])
        commodities = [str(c).strip() for c in commodities if str(c).strip()]
        if not commodities:
            continue

        label = str(event.get("risk_label") or "MEDIUM").upper()
        score = int(event.get("risk_score") or _label_to_score(label))
        headline = str(event.get("headline") or "")

        for commodity in set(commodities):
            key = commodity.lower()
            stat = crop_stats.setdefault(
                key,
                {
                    "crop": commodity,
                    "mentions": 0,
                    "max_label": "LOW",
                    "max_score": 0,
                    "avg_score_sum": 0,
                    "headlines": [],
                },
            )
            stat["mentions"] += 1
            stat["avg_score_sum"] += score
            if score >= stat["max_score"]:
                stat["max_score"] = score
                stat["max_label"] = label
            if headline and len(stat["headlines"]) < 3:
                stat["headlines"].append(headline)

    ranked: List[Dict[str, Any]] = []
    for stat in crop_stats.values():
        mentions = max(int(stat["mentions"]), 1)
        avg_score = round(float(stat["avg_score_sum"]) / mentions, 1)
        ranked.append(
            {
                "crop": stat["crop"],
                "risk_label": stat["max_label"],
                "risk_score": int(stat["max_score"]),
                "avg_risk_score": avg_score,
                "mentions": mentions,
                "headlines": stat["headlines"],
            }
        )
    ranked.sort(key=lambda x: (x["risk_score"], x["mentions"], x["avg_risk_score"]), reverse=True)

    query_summary = None
    if query_crop:
        q = query_crop.strip().lower()
        for item in ranked:
            crop_name = str(item["crop"]).lower()
            if q in crop_name or crop_name in q:
                query_summary = item
                break

    return {
        "query_crop": query_crop,
        "query_crop_risk": query_summary,
        "top_crop_risks": ranked[:6],
        "event_count_used": len(events),
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "events": store.event_count(),
        "advisories": store.advisory_count(),
        "chat_logs": store.chat_count(),
    }


@app.get("/api/dashboard")
async def dashboard():
    return store.get_dashboard_kpis()


@app.get("/api/events")
async def get_events(limit: int = 50):
    return store.get_events(limit)


@app.get("/api/advisories")
async def get_advisories(limit: int = 20):
    return store.get_advisories(limit)


@app.get("/api/trade/partners")
async def trade_partners():
    if data_loader:
        return data_loader.get_country_summary()
    return []


@app.get("/api/trade/commodities")
async def trade_commodities():
    if data_loader:
        return data_loader.get_commodity_summary()
    return []


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Manually trigger analysis for a custom headline."""
    if not orchestrator:
        raise HTTPException(503, "System not ready")
    background_tasks.add_task(orchestrator.analyze_headline, req.headline, req.source_url)
    return {"status": "queued", "headline": req.headline}


@app.post("/api/farmer/chat")
async def farmer_chat_query(req: FarmerChatRequest):
    if not farmer_chat or not data_loader:
        raise HTTPException(503, "System not ready")
    advisories = store.get_advisories(8)
    events = store.get_events(12)
    commodities = data_loader.get_commodity_summary() if data_loader else []
    inferred_country = (events[0].get("primary_country") if events else None)
    trade_facts = data_loader.get_trade_facts(
        crop=req.crop,
        country=inferred_country,
        limit=5,
    ) if data_loader else []
    response = await farmer_chat.respond(
        question=req.question,
        state=req.state,
        crop=req.crop,
        season=req.season,
        advisories=advisories,
        events=events,
        commodity_stats=commodities,
        trade_facts=trade_facts,
        crop_risk_context=_build_crop_risk_context(events, req.crop),
    )
    store.add_chat_log({
        "question": req.question,
        "state": req.state,
        "crop": req.crop,
        "season": req.season,
        "answer": response.get("answer", ""),
        "model_used": response.get("model_used", "unknown"),
        "generated_at": response.get("generated_at"),
    })
    return response


@app.get("/api/farmer/chat/logs")
async def farmer_chat_logs(limit: int = 50):
    return store.get_chat_logs(limit)


@app.get("/api/stats")
async def stats():
    return {
        "pipeline_interval_seconds": int(os.getenv("PIPELINE_INTERVAL_SECONDS", "300")),
        "total_events_processed": store.event_count(),
        "total_advisories_generated": store.advisory_count(),
        "total_chat_logs": store.chat_count(),
        "data_loaded": data_loader is not None and data_loader.loaded,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
