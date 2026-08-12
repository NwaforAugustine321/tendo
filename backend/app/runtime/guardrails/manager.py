from __future__ import annotations

from app.runtime.agents.run_context import RunContext
from app.runtime.llm.response import LLMResponse

from .base import Guardrail
from .decision import GuardrailDecision

from app.runtime.guardrails.guards.input_security import InputSafetyGuardrail
from app.runtime.guardrails.classifiers.nvidia import NvidiaSafetyClassifier


class GuardrailManager:
    """
    Coordinates all guardrails.

    Returns LLMResponse | None from check methods.
    None means continue normally.
    An LLMResponse means stop and return that response.
    """

    def __init__(
        self,
        guardrails: list[Guardrail] | None = None,
    ) -> None:

        classifier = NvidiaSafetyClassifier()
        self._input_guard = InputSafetyGuardrail(classifier=classifier)
        self._guardrails = guardrails or []

    @property
    def guardrails(
        self,
    ) -> list[Guardrail]:

        return self._guardrails

    def add(
        self,
        guardrail: Guardrail,
    ) -> None:

        self._guardrails.append(
            guardrail,
        )

    async def check_request(
        self,
        ctx: RunContext,
    ) -> LLMResponse | None:
        """
        Execute request guardrails.

        Returns None if the request should proceed.
        Returns an LLMResponse if the request is blocked.
        Raises RetryRequest if the request should retry.
        """

        for guardrail in self._guardrails:

            result = await guardrail.on_request(
                ctx,
            )

            match result.decision:

                case GuardrailDecision.CONTINUE:
                    continue

                case GuardrailDecision.STOP:
                    return LLMResponse(
                        text=f"This request is blocked\n Response message:\n{result.message}"
                        or f"This request is blocked"
                    )

                case GuardrailDecision.RETRY:
                    return LLMResponse(
                        text=result.message
                        or "Please try again.",
                    )

        return None

    async def check_response(
        self,
        ctx: RunContext,
        response: LLMResponse,
    ) -> LLMResponse | None:
        """
        Execute response guardrails.

        Returns None if the response should proceed.
        Returns an LLMResponse if the response is blocked.
        """

        for guardrail in self._guardrails:

            result = await guardrail.on_response(
                ctx,
                response,
            )

            match result.decision:

                case GuardrailDecision.CONTINUE:
                    continue

                case GuardrailDecision.STOP:
                    return LLMResponse(
                        text=f"This request is blocked\n Response message:\n{result.message}"
                        or "This request is blocked",
                    )

                case GuardrailDecision.REPLACE_RESPONSE:
                    if result.response is not None:
                        return result.response

                case GuardrailDecision.RETRY:
                    return LLMResponse(
                        text=result.message
                        or "Please try again.",
                    )

        return None
