"""ReflectionStage — evaluates execution quality and produces learning signals."""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from app.contexts.models import ExecutionContext
from app.execution.models import ReflectionOutput
from app.lib.json_parser import parse_json_output
from app.runtime import AgentRuntime, ToolBinder

logger = logging.getLogger(__name__)


class _ReflectionLLMOutput(BaseModel):
    candidate_skills: list[dict] = Field(default_factory=list)
    planner_feedback: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    observations: list[str] = Field(default_factory=list)


_REFLECTION_PROMPT = """Analyze the following agent execution and produce structured feedback.

## Execution Context
Objective: {objective}

## Execution Data
- Tools used: {tools_used}
- Knowledge used: {knowledge_used}
- Skills used: {skills_used}
- Iterations: {iterations}
- Duration: {duration_ms:.0f}ms

## Messages
{messages_summary}

## Domain Output
{domain_output}

Respond with a JSON object:
- candidate_skills: list of skill objects (each with "skill_id", "category", "content")
- planner_feedback: list of feedback strings for the planner
- confidence: float between 0.0 and 1.0
- observations: list of text observations about execution quality

Respond ONLY with valid JSON."""


class ReflectionStage:
    """Evaluates execution quality and produces learning signals.

    Does NOT write to any external system.
    Does NOT import, call, or read from the Event Store.
    """

    def __init__(self, llm: Any) -> None:
        self._llm = llm
        self._runtime = AgentRuntime(
            llm=llm,
            tool_binder=ToolBinder(),
            max_iter=5,
            max_validation_retries=1,
        )

    async def reflect(
        self,
        execution_context: ExecutionContext,
        messages: list[dict[str, Any]],
        tools_used: list[str],
        knowledge_used: list[str],
        skills_used: list[str],
        iterations: int,
        duration_ms: float,
        domain_output: dict[str, Any] | None,
    ) -> ReflectionOutput:
        messages_summary = self._summarize_messages(messages)

        prompt = _REFLECTION_PROMPT.format(
            objective=execution_context.objective,
            tools_used=", ".join(tools_used) if tools_used else "none",
            knowledge_used=", ".join(knowledge_used) if knowledge_used else "none",
            skills_used=", ".join(skills_used) if skills_used else "none",
            iterations=iterations,
            duration_ms=duration_ms,
            messages_summary=messages_summary,
            domain_output=json.dumps(domain_output or {}, default=str)[:2000],
        )

        raw = await self._invoke_runtime(prompt)

        try:
            data = parse_json_output(raw)
            if isinstance(data, dict):
                output = _ReflectionLLMOutput(**data)
                return ReflectionOutput(
                    candidate_skills=output.candidate_skills,
                    planner_feedback=output.planner_feedback,
                    confidence=max(0.0, min(1.0, output.confidence)),
                    observations=output.observations,
                )
        except Exception as e:
            logger.warning("Failed to parse reflection output: %s", e)

        return ReflectionOutput()

    async def _invoke_runtime(self, prompt: str) -> str:
        """Use AgentRuntime's invoke loop for structured LLM calls."""
        self._runtime._messages = [{"role": "user", "content": prompt}]
        self._runtime._iterations = 0
        self._runtime._tool_call_history = set()
        return await self._runtime._invoke_loop()

    @staticmethod
    def _summarize_messages(messages: list[dict[str, Any]]) -> str:
        if not messages:
            return "No messages recorded."
        return "\n".join(
            f"[{m.get('role', 'unknown')}]: {str(m.get('content', ''))[:200]}"
            for m in messages[-10:]
        )
