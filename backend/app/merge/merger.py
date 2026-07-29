

from __future__ import annotations
from pydantic import BaseModel, Field
from app.execution.models import Execution, ExecutionMetrics


class MergedResult(BaseModel):
    events: list[dict] = Field(default_factory=list)
    combined_output: dict = Field(default_factory=dict)
    reflection_summary: str = ""
    total_metrics: ExecutionMetrics = Field(default_factory=ExecutionMetrics)
    errors: list[str] = Field(default_factory=list)


class Merger:
    """Combines outputs from multiple Execution results."""

    async def merge(self, executions: list[Execution]) -> MergedResult:
        if len(executions) == 1:
            return self._pass_through(executions[0])
        return self._combine(executions)

    def _pass_through(self, execution: Execution) -> MergedResult:
        errors: list[str] = []
        if execution.error:
            errors.append(execution.error)

        return MergedResult(
            combined_output={
                "response": execution.result.response,
                "status": execution.result.status,
            },
            reflection_summary=self._summarize_reflection(execution),
            total_metrics=execution.metrics,
            errors=errors,
        )

    def _combine(self, executions: list[Execution]) -> MergedResult:
        combined_output: dict = {}
        reflections: list[str] = []
        errors: list[str] = []

        total_iterations = 0
        total_duration_ms = 0.0
        all_tools: list[dict] = []
        total_prompt_tokens = 0
        total_completion_tokens = 0

        for execution in executions:
            if execution.error:
                errors.append(f"{execution.error}")

            combined_output[execution.result.status] = execution.result.response

            reflection_text = self._summarize_reflection(execution)
            if reflection_text:
                reflections.append(reflection_text)

            total_iterations += execution.metrics.iterations
            total_duration_ms += execution.metrics.duration_ms
            all_tools.extend(execution.metrics.tools_invoked)
            total_prompt_tokens += execution.metrics.prompt_tokens
            total_completion_tokens += execution.metrics.completion_tokens

        total_metrics = ExecutionMetrics(
            iterations=total_iterations,
            duration_ms=total_duration_ms,
            tools_invoked=all_tools,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
        )

        return MergedResult(
            combined_output=combined_output,
            reflection_summary="\n".join(reflections),
            total_metrics=total_metrics,
            errors=errors,
        )

    @staticmethod
    def _summarize_reflection(execution: Execution) -> str:
        observations = execution.reflection.observations
        if not observations:
            return ""
        return "; ".join(observations)
