from __future__ import annotations

from app.runtime.agents.run_context import RunContext
from app.runtime.llm.response import LLMResponse

from ..base import Guardrail
from ..decision import GuardrailDecision
from ..result import GuardrailResult
from ..classifiers.base import SafetyClassifier


class OutputSafetyGuardrail(Guardrail):
    """
    Validates the generated response before it is
    returned to the user.
    """

    def __init__(
        self,
        classifier: SafetyClassifier,
    ) -> None:

        self._classifier = classifier

    async def on_response(
        self,
        ctx: RunContext,
        response: LLMResponse,
    ) -> GuardrailResult:

        if not response.text:
            return GuardrailResult()

        result = await self._classifier.classify(
            response.text,
        )

        if result.user_safety == "unsafe":

            return GuardrailResult(
                decision=GuardrailDecision.REPLACE_RESPONSE,
                response=LLMResponse(
                    text=result.refusal_message,
                    output=None,
                    tool_calls=[],
                    metadata={},
                ),
            )

        return GuardrailResult()
