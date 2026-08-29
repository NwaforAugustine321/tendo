from __future__ import annotations

from abc import ABC, abstractmethod

from app.runtime.chat.message import ChatMessage


class Summarizer(ABC):
    """
    Summarizer.
    """

    @abstractmethod
    async def summarize(
        self,
        *,
        messages: list[ChatMessage],
        target_tokens: int,
        instructions: str | None = None,
    ) -> str:
        ...
