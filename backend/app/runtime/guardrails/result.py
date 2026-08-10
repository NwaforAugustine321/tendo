from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.runtime.llm.response import LLMResponse

from .decision import GuardrailDecision


from typing import Literal

from pydantic import BaseModel


class SafetyResult(BaseModel):

    user_safety: Literal[
        "safe",
        "unsafe",
    ]

    response: str = ""


@dataclass(slots=True)
class GuardrailResult:
    """
    Result returned by a guardrail.
    """

    decision: GuardrailDecision = (
        GuardrailDecision.CONTINUE
    )

    message: str | None = None

    response: LLMResponse | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    @property
    def should_stop(self) -> bool:
        return self.decision is not GuardrailDecision.CONTINUE
