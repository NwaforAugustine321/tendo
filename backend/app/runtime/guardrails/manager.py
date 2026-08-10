from __future__ import annotations

from app.runtime.agents.run_context import RunContext
from app.runtime.llm.response import LLMResponse

from .base import Guardrail
from .decision import GuardrailDecision
from .exceptions import GuardrailViolation, RetryRequest


class GuardrailManager:
    """
    Coordinates all guardrails.

    The runner should never inspect GuardrailDecision
    directly. This manager is responsible for applying
    the guardrail policy.
    """

    def __init__(
        self,
        guardrails: list[Guardrail] | None = None,
    ) -> None:

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
    ) -> None:
        """
        Execute request guardrails.

        Raises GuardrailViolation if the request
        should not continue.
        """

        for guardrail in self._guardrails:

            result = await guardrail.on_request(
                ctx,
            )

            match result.decision:

                case GuardrailDecision.CONTINUE:
                    continue

                case GuardrailDecision.STOP:
                    raise GuardrailViolation(
                        result.message
                        or "Request blocked by guardrail."
                    )

                case GuardrailDecision.RETRY:
                    raise RetryRequest()

                case GuardrailDecision.REPLACE_RESPONSE:
                    raise RuntimeError(
                        "Request guardrails cannot replace responses."
                    )

    async def check_response(
        self,
        ctx: RunContext,
        response: LLMResponse,
    ) -> LLMResponse:
        """
        Execute response guardrails.

        Returns the final approved response.
        """

        current = response

        for guardrail in self._guardrails:

            result = await guardrail.on_response(
                ctx,
                current,
            )

            match result.decision:

                case GuardrailDecision.CONTINUE:
                    continue

                case GuardrailDecision.STOP:
                    raise GuardrailViolation(
                        result.message
                        or "Response blocked by guardrail."
                    )

                case GuardrailDecision.REPLACE_RESPONSE:

                    if result.response is None:
                        raise RuntimeError(
                            "Guardrail requested "
                            "REPLACE_RESPONSE but "
                            "returned no response."
                        )

                    current = result.response

                case GuardrailDecision.RETRY:
                    raise RetryRequest()

        return current
