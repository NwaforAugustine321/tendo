from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..exception import ContextOptimizationFailed


@dataclass(slots=True)
class OptimizationResult:
    """
    Result of one optimization pass.
    """

    optimized: bool
    exhausted: bool = False
    estimated_tokens_saved: int = 0
    reason: str = ""


class ContextOptimizer(ABC):
    """
    Base interface for provider-specific
    context optimizers.
    """

    @abstractmethod
    async def optimize(
        self,
        *,
        conversation: ConversationContext,
        target_tokens: int,
    ) -> OptimizationResult:
        """
        Attempt one optimization pass.
        """
        ...
