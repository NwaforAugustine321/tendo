from abc import ABC, abstractmethod

from app.runtime.chat.message import ChatMessage


class TokenCounter(ABC):

    @abstractmethod
    async def count(
        self,
        messages: list[ChatMessage],
    ) -> int:
        ...


class DefaultTokenCounter(
    TokenCounter,
):

    async def count(
        self,
        messages: list[ChatMessage],
    ) -> int:

        return sum(
            len(message.content.split())
            for message in messages
        )
