

from __future__ import annotations
from pydantic import BaseModel, Field


class Result(BaseModel):
    status: str = "success"
    response: str = ""


class ExecutionMetrics(BaseModel):
    iterations: int = 0
    duration_ms: float = 0.0
    tools_invoked: list[dict] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ReflectionOutput(BaseModel):
    candidate_skills: list[dict] = Field(default_factory=list)
    planner_feedback: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    observations: list[str] = Field(default_factory=list)


class Execution(BaseModel):
    result: Result
    reflection: ReflectionOutput = Field(default_factory=ReflectionOutput)
    metrics: ExecutionMetrics = Field(default_factory=ExecutionMetrics)
    error: str | None = None
