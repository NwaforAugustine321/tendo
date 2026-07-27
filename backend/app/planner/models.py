"""Pydantic models for the Planner's ExecutionPlan output."""

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from app.contexts.models import ExecutionContext, SharedContext


class ExecutionOrder(str, Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"


class AgentAssignment(BaseModel):
    agent_id: str
    execution_context: ExecutionContext
    depends_on: list[str] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    participating_agents: list[AgentAssignment] = Field(default_factory=list)
    execution_order: ExecutionOrder
    shared_context: SharedContext
    unresolvable: bool = False
    unresolvable_reason: str | None = None

    @model_validator(mode="after")
    def validate_agents_present_when_resolvable(self) -> "ExecutionPlan":
        if not self.unresolvable and len(self.participating_agents) < 1:
            raise ValueError(
                "participating_agents must contain at least one agent "
                "when the plan is not marked as unresolvable"
            )
        return self
