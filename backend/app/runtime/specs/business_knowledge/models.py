from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    COMPLETED = "completed"
    NEEDS_RETRIEVAL = "needs_retrieval"
    NO_CHANGES = "no_changes"


class InsightEntry(BaseModel):
    insight: str = Field(description="Natural language business understanding. Full interpretation, not raw data.")
    area: str = Field(default="general", description="Business area: sales, operations, finance, hr, inventory, customers, marketing, general")
    importance: float = Field(ge=0.0, le=1.0, default=0.5, description="How critical: routine=0.3, notable=0.6, critical=0.9")
    timestamp: str = Field(default="", description="ISO 8601 timestamp of when the event occurred")
    payload: dict[str, Any] = Field(default_factory=dict, description="Flexible JSON with evidence, links, entities, confidence, patterns, and any contextual data")


class InsightOutput(BaseModel):
    status: AgentStatus = Field(default=AgentStatus.COMPLETED, description="completed, needs_retrieval, or no_changes")
    insights: list[InsightEntry] = Field(default_factory=list, description="List of business insights from this event batch")
    reasoning_summary: str = Field(default="", description="Brief explanation of what was learned")
    business_id: str = ""
    job_id: str = ""


class IntelligenceError(Exception):
    pass


class AgentError(IntelligenceError):
    def __init__(self, message: str, iteration: int = 0, partial_understanding: str = ""):
        self.iteration = iteration
        self.partial_understanding = partial_understanding
        super().__init__(message)


class ExecutionError(IntelligenceError):
    pass
