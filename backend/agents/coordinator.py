"""Agent Coordinator - Orchestrates the 4-agent research pipeline."""
import asyncio
import json
import logging
import time
from typing import Optional
from agents.paper_hunter import PaperHunterAgent
from agents.synthesis_agent import SynthesisAgent
from agents.writing_agent import WritingAgent
from agents.verification_agent import VerificationAgent

logger = logging.getLogger(__name__)


class AgentCoordinator:
    """
    Coordinates the 4-agent pipeline:
    1. Paper Hunter → Find papers
    2. Synthesis Agent → Analyze papers
    3. Writing Agent → Generate literature review
    4. Verification Agent → Fact-check everything
    
    Broadcasts real-time status updates via WebSocket.
    """

    def __init__(self):
        self.paper_hunter = PaperHunterAgent()
        self.synthesis = SynthesisAgent()
        self.writer = WritingAgent()
        self.verifier = VerificationAgent()
        self.agents = [self.paper_hunter, self.synthesis, self.writer, self.verifier]
        self.websocket_connections = {}
        self.research_results = {}

    def get_all_status(self) -> list:
        """Get status of all agents."""
        return [agent.get_status() for agent in self.agents]

    async def run_pipeline(
        self,
        research_id: str,
        topic: str,
        domain: str = "custom",
        year_start: int = 2020,
        year_end: int = 2026,
        min_citations: int = 0,
        max_papers: int = 100,
        citation_format: str = "apa",
    ) -> dict:
        """Run the full 4-agent research pipeline."""
        start_time = time.time()

        # Reset all agents
        for agent in self.agents:
            agent.reset()

        context = {
            "research_id": research_id,
            "topic": topic,
            "domain": domain,
            "year_start": year_start,
            "year_end": year_end,
            "min_citations": min_citations,
            "max_papers": max_papers,
            "citation_format": citation_format,
        }

        try:
            # ── Stage 1: Paper Hunter ─────────────────────────────
            await self._broadcast(research_id, "stage", {
                "stage": 1,
                "name": "Paper Hunter",
                "status": "running",
            })
            hunt_result = await self.paper_hunter.run(context)
            await self._broadcast(research_id, "agent_update", self.paper_hunter.get_status())

            if "error" in hunt_result:
                return self._error_result(research_id, "Paper Hunter failed", hunt_result)

            papers = hunt_result.get("papers", [])
            context["papers"] = papers

            # ── Stage 2: Synthesis Agent ──────────────────────────
            await self._broadcast(research_id, "stage", {
                "stage": 2,
                "name": "Synthesis Agent",
                "status": "running",
            })
            analysis_result = await self.synthesis.run(context)
            await self._broadcast(research_id, "agent_update", self.synthesis.get_status())

            if "error" in analysis_result and not analysis_result.get("themes"):
                return self._error_result(research_id, "Synthesis failed", analysis_result)

            context["analysis"] = analysis_result

            # ── Stage 3: Writing Agent ────────────────────────────
            await self._broadcast(research_id, "stage", {
                "stage": 3,
                "name": "Writing Agent",
                "status": "running",
            })
            writing_result = await self.writer.run(context)
            await self._broadcast(research_id, "agent_update", self.writer.get_status())

            if "error" in writing_result and not writing_result.get("document"):
                return self._error_result(research_id, "Writing failed", writing_result)

            context["document"] = writing_result.get("document", {})
            context["claims"] = writing_result.get("claims", [])

            # ── Stage 4: Verification Agent ───────────────────────
            await self._broadcast(research_id, "stage", {
                "stage": 4,
                "name": "Verification Agent",
                "status": "running",
            })
            verification_result = await self.verifier.run(context)
            await self._broadcast(research_id, "agent_update", self.verifier.get_status())

            # ── Compile Final Results ─────────────────────────────
            elapsed = round(time.time() - start_time, 1)

            result = {
                "research_id": research_id,
                "topic": topic,
                "domain": domain,
                "status": "completed",
                "elapsed_seconds": elapsed,
                "papers": {
                    "total_found": hunt_result.get("total_found", 0),
                    "unique_count": hunt_result.get("unique_count", 0),
                    "final_count": hunt_result.get("final_count", 0),
                    "queries_used": hunt_result.get("queries_used", []),
                    "items": papers[:50],  # Limit for response size
                },
                "analysis": {
                    "themes": analysis_result.get("themes", []),
                    "contradictions": analysis_result.get("contradictions", []),
                    "trends": analysis_result.get("trends", {}),
                    "gaps": analysis_result.get("gaps", []),
                    "summaries": analysis_result.get("summaries", []),
                    "top_authors": analysis_result.get("top_authors", []),
                },
                "document": writing_result.get("document", {}),
                "verification": {
                    "overall_confidence": verification_result.get("overall_confidence", 0),
                    "verified_count": verification_result.get("verified_count", 0),
                    "flagged_count": verification_result.get("flagged_count", 0),
                    "total_claims": verification_result.get("total_claims", 0),
                    "plagiarism_report": verification_result.get("plagiarism_report", {}),
                    "ethical_badge": verification_result.get("ethical_badge", {}),
                    "summary": verification_result.get("verification_summary", ""),
                    "claims": verification_result.get("verified_claims", [])[:20],
                },
                "agent_status": self.get_all_status(),
            }

            self.research_results[research_id] = result
            await self._broadcast(research_id, "completed", {
                "research_id": research_id,
                "elapsed_seconds": elapsed,
            })

            return result

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return self._error_result(research_id, str(e), {})

    def _error_result(self, research_id: str, error: str, details: dict) -> dict:
        return {
            "research_id": research_id,
            "status": "error",
            "error": error,
            "details": details,
            "agent_status": self.get_all_status(),
        }

    async def _broadcast(self, research_id: str, event_type: str, data: dict):
        """Broadcast status update via WebSocket."""
        ws = self.websocket_connections.get(research_id)
        if ws:
            try:
                message = json.dumps({
                    "type": event_type,
                    "data": data,
                    "agent_status": self.get_all_status(),
                })
                await ws.send_text(message)
            except Exception as e:
                logger.debug(f"WebSocket broadcast error: {e}")

    def register_websocket(self, research_id: str, websocket):
        """Register a WebSocket connection for a research session."""
        self.websocket_connections[research_id] = websocket

    def unregister_websocket(self, research_id: str):
        """Unregister a WebSocket connection."""
        self.websocket_connections.pop(research_id, None)

    def get_result(self, research_id: str) -> Optional[dict]:
        """Get cached result for a research session."""
        return self.research_results.get(research_id)


coordinator = AgentCoordinator()
