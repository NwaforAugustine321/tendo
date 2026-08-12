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
    Coordinates prompt optimization before inference.
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
        return self._strategy

    async def build(
        self,
        builder: PromptBuilder,
    ) -> list[ChatMessage]:

        return await self._strategy.build(
            builder,
        )
