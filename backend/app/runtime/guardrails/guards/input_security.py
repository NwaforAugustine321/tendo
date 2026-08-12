from __future__ import annotations

from app.runtime.agents.run_context import RunContext

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

        message = ctx.current_user_message

        if message is None:
            return GuardrailResult()

        content = (
            message.content
            if isinstance(message.content, str)
            else str(message.content)
        )

        if not content:
            return GuardrailResult()

        result = await self._classifier.classify(
            content,
        )

        print('guard input', result)

        if result.user_safety == "unsafe":

            return GuardrailResult(
                decision=GuardrailDecision.STOP,
                message=result.refusal_message,
            )

        return GuardrailResult()
