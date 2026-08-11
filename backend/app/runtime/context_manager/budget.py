from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ContextBudget:
    """
    Token budget for one inference.
    """

    max_input_tokens: int

    reserved_output_tokens: int

    @property
    def available_tokens(self) -> int:

        return (
            self.max_input_tokens
            - self.reserved_output_tokens
        )
