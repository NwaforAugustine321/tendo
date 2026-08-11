from __future__ import annotations

from app.runtime.chat.message import ChatMessage

from .context import ConversationContext
from .in_memory_store import InMemConversationStore
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
        store: ConversationStore | None = None,
        namespace: str,
    ) -> None:

        self._store = (
            store
            if store is not None
            else InMemConversationStore(
                namespace=namespace,
            )
        )

    @property
    def store(
        self,
    ) -> ConversationStore:
        return self._store

    def middleware(
        self,
    ) -> list:
        """
        Return middleware instances contributed by this provider.
        """

        from app.runtime.middlewares.conversation import (
            ConversationMiddleware,
        )

        return [
            ConversationMiddleware(
                provider=self,
            )
        ]

    async def load(
        self,
        *,
        conversation_id: str,
    ) -> ConversationContext:
        """
        Load a conversation or create an empty one.
        """

        conversation = await self._store.load(
            conversation_id=conversation_id,
        )

        if conversation is None:
            conversation = ConversationContext(
                conversation_id=conversation_id,
            )

        return conversation

    async def save(
        self,
        *,
        conversation: ConversationContext,
    ) -> None:
        """
        Persist a conversation.
        """

        await self._store.save(
            conversation=conversation,
        )

    async def append(
        self,
        *,
        conversation: ConversationContext,
        message: ChatMessage,
    ) -> None:
        """
        Append a single message.
        """

        conversation.messages.append(
            message,
        )

        await self.save(
            conversation=conversation,
        )

    async def append_many(
        self,
        *,
        conversation: ConversationContext,
        messages: list[ChatMessage],
    ) -> None:
        """
        Append multiple messages.
        """

        if not messages:
            return

        conversation.messages.extend(
            messages,
        )

        await self.save(
            conversation=conversation,
        )

    async def clear(
        self,
        *,
        conversation: ConversationContext,
    ) -> None:
        """
        Remove the conversation from storage and reset
        the in-memory context.
        """

        await self._store.delete(
            conversation_id=conversation.conversation_id,
        )

        conversation.messages.clear()
        conversation.summary = None
