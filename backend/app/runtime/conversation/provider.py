from __future__ import annotations

from app.runtime.chat.message import ChatMessage

from .context import ConversationContext
from .store import ConversationStore


class ConversationProvider:
    """
    Coordinates conversation state.

    The provider keeps the in-memory ConversationContext
    synchronized with the underlying ConversationStore.
    """

    def __init__(
        self,
        *,
        store: ConversationStore,
    ) -> None:

        self._store = store

    @property
    def store(
        self,
    ) -> ConversationStore:

        return self._store

    def middleware(self) -> list:
        """
        Return middleware instances that this provider
        contributes to the agent lifecycle.
        """

        from app.runtime.middlewares.conversation import (
            ConversationMiddleware,
        )

        return [
            ConversationMiddleware(provider=self),
        ]

    async def load(
        self,
        *,
        conversation_id: str,
    ) -> ConversationContext:

        return await self._store.load(
            conversation_id=conversation_id,
        )

    async def append(
        self,
        *,
        conversation: ConversationContext,
        message: ChatMessage,
    ) -> None:

        conversation.messages.append(
            message,
        )

        await self._store.save(
            conversation=conversation,
        )

    async def append_many(
        self,
        *,
        conversation: ConversationContext,
        messages: list[ChatMessage],
    ) -> None:

        if not messages:
            return

        conversation.messages.extend(
            messages,
        )

        await self._store.save(
            conversation=conversation,
        )

    async def clear(
        self,
        *,
        conversation: ConversationContext,
    ) -> None:

        conversation.messages.clear()

        conversation.summary = None

        await self._store.save(
            conversation=conversation,
        )
