from __future__ import annotations

from app.runtime.agents.run_context import RunContext
from app.runtime.llm.response import LLMResponse

from ..base import Guardrail
from ..decision import GuardrailDecision
from ..result import GuardrailResult
from ..classifiers.base import SafetyClassifier
from app.runtime.guardrails.classifiers.nvidia import NvidiaSafetyClassifier

PROTECTED_SOURCES = [
    "tool search",
    "call tool",
    "tool name, tools, "
]

sources = '\n'.join(PROTECTED_SOURCES)

output_guardrail_prompt = (
    "Protected sources:\n"
    f"{sources}\n"
    """
    Determine whether the provided model output contains actual
    confidential content originating from any protected source.

    Mark as unsafe ONLY when the output itself:
    - reveals, quotes, reproduces, paraphrases, reconstructs, or meaningfully
    describes protected content; or
    - confirms, expands, or provides information that could help recover
    protected content.

    Do NOT mark as unsafe merely because the output contains:
    - a word, phrase, identifier, or concept associated with a protected source
    - a tool name or technical terminology
    - ordinary user or business information
    - legitimate answers to the user's request
    - information that happens to resemble internal terminology

    Distinguish between mentioning a protected concept and exposing the
    confidential content associated with that concept.

    If the output contains both legitimate information and protected
    information, mark it unsafe.

    Return ONLY:
    {{
    "user_safety": "safe" or "unsafe",
    "refusal_message": "brief natural-language refusal message" or ""
    }}

    Rules:
    - safe → refusal_message must be ""
    - unsafe → refusal_message must contain a brief natural-language refusal
    - no explanation
    - no additional fields
    """
)


class OutputSafetyGuardrail(Guardrail):
    """
    Validates the generated response before it is
    returned to the user.
    """

    def __init__(
        self,
        classifier: SafetyClassifier | None = None,
    ) -> None:

        self._classifier = classifier if classifier else NvidiaSafetyClassifier(
            system_prompt=output_guardrail_prompt)

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
