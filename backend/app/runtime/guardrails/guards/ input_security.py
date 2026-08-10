from __future__ import annotations

from app.agents.run_context import RunContext

from ..base import Guardrail
from ..decision import GuardrailDecision
from ..result import GuardrailResult
from ..classifiers.base import SafetyClassifier


class InputSafetyGuardrail(Guardrail):
    """
    Validates the latest user message before the LLM
    executes.
    """

    def __init__(
        self,
        classifier: SafetyClassifier,
    ) -> None:

        self._classifier = classifier

    async def on_request(
        self,
        ctx: RunContext,
    ) -> GuardrailResult:

        if not ctx.chat_context.messages:
            return GuardrailResult()

        message = ctx.chat_context.messages[-1]

        if message.role != "user":
            return GuardrailResult()

        result = await self._classifier.classify(
            message.content,
        )

        if result.user_safety == "unsafe":

            return GuardrailResult(
                decision=GuardrailDecision.STOP,
                message=result.response,
            )

        return GuardrailResult()
