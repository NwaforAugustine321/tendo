from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.runtime.chat.message import ChatMessage
    from app.runtime.prompts.builder import PromptBuilder


class ContextStrategy(ABC):
    """
    Strategy used by ContextManager to optimize
    prompts before inference.
    """

    @abstractmethod
    async def build(
        self,
        builder: PromptBuilder,
    ) -> list[ChatMessage]:
        ...
