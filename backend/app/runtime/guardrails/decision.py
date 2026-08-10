from __future__ import annotations

from enum import Enum


class GuardrailDecision(str, Enum):
    """
    The action requested by a guardrail.
    """

    CONTINUE = "continue"

    STOP = "stop"

    REPLACE_RESPONSE = "replace"

    RETRY = "retry"
