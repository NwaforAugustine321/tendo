from typing import Any

from pydantic import BaseModel, Field

from app.business_knowledge.models import InsightEntry


class SubInsightOutput(BaseModel):
    insights: list[InsightEntry] = Field(default_factory=list, description="Business insights produced by this sub-agent")
    reasoning: str = Field(default="", description="Agent's reasoning about the knowledge it found")


class DelegationDecision(BaseModel):
    agent_name: str = Field(description="Name of the sub-insight agent delegated to")
    reason: str = Field(default="", description="Why this agent was selected")


class DispatcherOutput(BaseModel):
    delegations: list[DelegationDecision] = Field(default_factory=list, description="List of delegation decisions made")
