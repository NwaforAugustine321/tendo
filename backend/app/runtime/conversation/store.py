from abc import ABC, abstractmethod
from typing import Any

from .context import ConversationContext


class ConversationStore(ABC):

    @abstractmethod
    async def save(
        self,
        *,
        conversation: ConversationContext,
    ) -> None:
        ...

    @abstractmethod
    async def load(
        self,
        **kwargs: Any,
    ) -> ConversationContext | None:
        ...

    @abstractmethod
    async def find_all(
        self,
        **kwargs: Any,
    ) -> list[ConversationContext]:
        ...

    @abstractmethod
    async def delete(
        self,
        **kwargs: Any,
    ) -> None:
        ...
