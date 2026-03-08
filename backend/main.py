"""
AgroShield - Geopolitical Agricultural Trade Intelligence System
FastAPI Backend: Multi-agent pipeline + Amazon Bedrock advisory generation
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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


@app.get("/api/health")
async def health():
    return {"status": "ok", "events": store.event_count(), "advisories": store.advisory_count()}


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
    return await farmer_chat.respond(
        question=req.question,
        state=req.state,
        crop=req.crop,
        season=req.season,
        advisories=advisories,
        events=events,
        commodity_stats=commodities,
    )


@app.get("/api/stats")
async def stats():
    return {
        "pipeline_interval_seconds": int(os.getenv("PIPELINE_INTERVAL_SECONDS", "300")),
        "total_events_processed": store.event_count(),
        "total_advisories_generated": store.advisory_count(),
        "data_loaded": data_loader is not None and data_loader.loaded,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
