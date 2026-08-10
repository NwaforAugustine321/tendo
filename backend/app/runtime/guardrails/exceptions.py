from __future__ import annotations


class GuardrailError(RuntimeError):
    """
    Base exception for all guardrail-related errors.
    """


class GuardrailViolation(GuardrailError):
    """
    Raised when a guardrail blocks the current request
    or response.
    """

    def __init__(
        self,
        message: str = "Guardrail blocked execution.",
    ) -> None:
        super().__init__(message)


class RetryRequest(GuardrailError):
    """
    Raised when a guardrail requests the current iteration
    to be retried.
    """

    def __init__(
        self,
        message: str = "Guardrail requested retry.",
    ) -> None:
        super().__init__(message)
