from __future__ import annotations

from abc import ABC

from app.runtime.llm.response import LLMResponse

from app.runtime.agents.run_context import RunContext

from .result import GuardrailResult


class Guardrail(ABC):
    """
    Base class for all guardrails.
    """

    async def on_request(
        self,
        ctx: RunContext,
    ) -> GuardrailResult:

        return GuardrailResult()

    async def on_response(
        self,
        ctx: RunContext,
        response: LLMResponse,
    ) -> GuardrailResult:

        return GuardrailResult()
