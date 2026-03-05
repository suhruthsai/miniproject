"""Base agent class for all specialized research agents."""
import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class BaseAgent(ABC):
    """Abstract base class for research agents."""

    def __init__(self, name: str, description: str, icon: str):
        self.name = name
        self.description = description
        self.icon = icon
        self.status = AgentStatus.IDLE
        self.progress = 0
        self.current_step = ""
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.logger = logging.getLogger(f"agent.{name}")

    @abstractmethod
    async def execute(self, context: dict) -> dict:
        """Execute the agent's task. Must be implemented by subclasses."""
        pass

    async def run(self, context: dict) -> dict:
        """Run the agent with status tracking and error handling."""
        self.status = AgentStatus.RUNNING
        self.progress = 0
        self.error = None
        self.start_time = time.time()

        try:
            self.result = await self.execute(context)
            self.status = AgentStatus.COMPLETED
            self.progress = 100
            self.end_time = time.time()
            return self.result
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.error = str(e)
            self.end_time = time.time()
            self.logger.error(f"Agent {self.name} failed: {e}")
            return {"error": str(e)}

    def update_progress(self, progress: int, step: str = ""):
        """Update agent progress for real-time status display."""
        self.progress = min(progress, 100)
        if step:
            self.current_step = step
        self.logger.info(f"[{self.name}] {progress}% - {step}")

    def get_status(self) -> dict:
        """Get current agent status for WebSocket broadcasting."""
        elapsed = 0
        if self.start_time:
            end = self.end_time or time.time()
            elapsed = round(end - self.start_time, 1)

        return {
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "status": self.status.value,
            "progress": self.progress,
            "current_step": self.current_step,
            "elapsed_seconds": elapsed,
            "error": self.error,
        }

    def reset(self):
        """Reset agent state for new execution."""
        self.status = AgentStatus.IDLE
        self.progress = 0
        self.current_step = ""
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
