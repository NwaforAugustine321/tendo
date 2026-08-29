from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.runtime.chat.message import ChatMessage
    from app.runtime.prompts.builder import PromptBuilder

from .strateges.default_context_strategy import (
    DefaultContextStrategy,
)
from .strateges.strategy import (
    ContextStrategy,
)


class ContextManager:
    """
    Coordinates prompt construction and conversation
    optimization.

    The manager does not decide when optimization is needed.
    The ContextMonitor and runtime determine that.

    The manager simply delegates context operations to
    the configured ContextStrategy.
    """

    def __init__(
        self,
        *,
        strategy: ContextStrategy | None = None,
    ) -> None:

        self._strategy = (
            strategy
            if strategy is not None
            else DefaultContextStrategy()
        )

    @property
    def strategy(
        self,
    ) -> ContextStrategy:
        """
        Configured context strategy.
        """

        return self._strategy

    async def build(
        self,
        builder: PromptBuilder,
    ) -> list[ChatMessage]:
        """
        Build the prompt for LLM inference.
        """

        return await self._strategy.build(
            builder,
        )

    async def optimize(
        self,
        builder: PromptBuilder,
    ) -> bool:
        """
        Optimize the conversation after the context
        threshold has been reached.

        Returns
        -------
        bool
            True when the conversation was successfully
            optimized, otherwise False.
        """

        return await self._strategy.optimize(
            builder,
        )
