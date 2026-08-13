from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.runtime.llm.llm import LLM


@dataclass(slots=True)
class ContextBudget:
    """
    Represents the token budget available for one
    model inference.

    ContextBudget describes the LLM's hard context
    constraints.

    It does not decide when conversation optimization
    should happen. That responsibility belongs to
    ContextMonitor.
    """

    max_context_tokens: int | None

    reserved_output_tokens: int

    @property
    def max_prompt_tokens(
        self,
    ) -> int | None:
        """
        Maximum number of tokens available for the
        input prompt after reserving output tokens.

        This represents the model's hard prompt limit.
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
        Create a ContextBudget from the LLM configuration.
        """

        return cls(
            max_context_tokens=(
                llm.max_context_tokens
            ),
            reserved_output_tokens=(
                llm.max_output_tokens
            ),
        )
