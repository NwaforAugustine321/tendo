from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.runtime.conversation.context import (
        ConversationContext,
    )

from app.runtime.agents.run_context import RunContext


@dataclass(slots=True)
class OptimizationResult:
    """
    Result of one conversation optimization pass.
    """

    optimized: bool

    exhausted: bool = False

    estimated_tokens_saved: int = 0

    reason: str = ""


class ContextOptimizer(ABC):
    """
    Base interface for provider-specific conversation
    optimizers.

    A ContextOptimizer performs the actual optimization
    of a ConversationContext.

    It does not:

    - build prompts
    - count tokens
    - decide when optimization is required
    - manage runtime execution state

    The current token count is supplied by the runtime
    because it has already been calculated by the
    ContextMonitor.
    """

    @abstractmethod
    async def optimize(
        self,
        *,
        conversation: ConversationContext,
        current_tokens: int,
        target_tokens: int,
        run_context: RunContext
    ) -> OptimizationResult:
        """
        Attempt one conversation optimization pass.

        Parameters
        ----------
        conversation:
            Conversation context to optimize.

        current_tokens:
            Approximate token count already calculated
            by the ContextMonitor.

        target_tokens:
            Desired approximate token size after
            optimization.

        Returns
        -------
        OptimizationResult
            Result describing whether optimization
            occurred.
        """
        ...
