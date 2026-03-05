"""Research API routes."""
import uuid
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional
from agents.coordinator import coordinator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["research"])


class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=500, description="Research topic")
    domain: str = Field(default="custom", description="Research domain")
    year_start: int = Field(default=2020, ge=1900, le=2030)
    year_end: int = Field(default=2026, ge=1900, le=2030)
    min_citations: int = Field(default=0, ge=0)
    max_papers: int = Field(default=100, ge=10, le=500)
    citation_format: str = Field(default="apa", pattern="^(apa|ieee|harvard)$")


@router.post("/research")
async def start_research(request: ResearchRequest):
    """Start a new research pipeline."""
    research_id = str(uuid.uuid4())[:8]

    # Run pipeline in background
    asyncio.create_task(
        coordinator.run_pipeline(
            research_id=research_id,
            topic=request.topic,
            domain=request.domain,
            year_start=request.year_start,
            year_end=request.year_end,
            min_citations=request.min_citations,
            max_papers=request.max_papers,
            citation_format=request.citation_format,
        )
    )

    return {
        "research_id": research_id,
        "status": "started",
        "topic": request.topic,
        "message": f"Research pipeline started. Connect to WebSocket /ws/research/{research_id} for updates.",
    }


@router.get("/research/{research_id}")
async def get_research_result(research_id: str):
    """Get research results by ID."""
    result = coordinator.get_result(research_id)
    if result:
        return result
    return {
        "research_id": research_id,
        "status": "in_progress",
        "agent_status": coordinator.get_all_status(),
    }


@router.get("/agents/status")
async def get_agent_status():
    """Get current status of all agents."""
    return {"agents": coordinator.get_all_status()}


@router.websocket("/ws/research/{research_id}")
async def research_websocket(websocket: WebSocket, research_id: str):
    """WebSocket for real-time research pipeline status updates."""
    await websocket.accept()
    coordinator.register_websocket(research_id, websocket)

    try:
        while True:
            # Keep connection alive and forward any client messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        coordinator.unregister_websocket(research_id)
    except Exception:
        coordinator.unregister_websocket(research_id)
