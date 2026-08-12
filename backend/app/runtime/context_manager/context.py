from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.runtime.llm.llm import LLM


@dataclass(slots=True)
class ContextBudget:
    """
    Represents the available token budget for one
    model inference.
    """

    max_context_tokens: int | None

    reserved_output_tokens: int

    @property
    def max_prompt_tokens(
        self,
    ) -> int | None:
        """
        Maximum number of tokens available for the
        input prompt.
        """

        if self.max_context_tokens is None:
            return None

        return max(
            0,
            self.max_context_tokens
            - self.reserved_output_tokens,
        )

    @classmethod
    def from_llm(
        cls,
        llm: LLM,
    ) -> ContextBudget:
        """
        Create a ContextBudget from an LLM
        configuration.
        """

        return cls(
            max_context_tokens=llm.max_context_tokens,
            reserved_output_tokens=llm.max_output_tokens,
        )
