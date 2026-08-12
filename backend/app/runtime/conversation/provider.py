from __future__ import annotations

from app.runtime.chat.message import ChatMessage

from .context import ConversationContext
from .in_memory_store import InMemConversationStore
from .store import ConversationStore
from app.runtime.context_manager.optimizers.optimizer import (
    ContextOptimizer as Optimizer,
    OptimizationResult,
)
from app.runtime.context_manager.optimizers.default_optimizer import (
    DefaultConversationOptimizer,
)


class ConversationProvider:
    """
    Coordinates conversation persistence.

    Responsibilities
    ----------------
    - Load conversation metadata and messages.
    - Persist conversation metadata.
    - Append conversation messages.
    - Update conversation summaries.
    - Clear conversations.
    """

    def __init__(
        self,
        *,
        namespace: str,
        store: ConversationStore | None = None,
        optimizer: Optimizer | None = None,
    ) -> None:

        self._store = (
            store
            if store is not None
            else InMemConversationStore(
                namespace=namespace,
            )
        )

        self._optimizer = (
            optimizer
            or DefaultConversationOptimizer(
                provider=self,
            )
        )

    async def optimize(
        self,
        *,
        conversation: ConversationContext,
        target_tokens: int,
    ) -> OptimizationResult:

        return await self._optimizer.optimize(
            conversation=conversation,
            target_tokens=target_tokens,
        )

    @property
    def store(
        self,
    ) -> ConversationStore:
        return self._store

    def middleware(
        self,
    ) -> list:

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
        message_limit: int | None = None,
    ) -> ConversationContext:
        """
        Load a conversation.

        Conversation metadata and messages are
        loaded independently and combined into
        a runtime ConversationContext.
        """

        conversation = (
            await self._store.load_conversation(
                conversation_id=conversation_id,
            )
        )

        if conversation is None:

            conversation = ConversationContext(
                conversation_id=conversation_id,
            )

        conversation.messages = (
            await self._store.load_messages(
                conversation_id=conversation_id,
                limit=message_limit,
            )
        )

        return conversation

    async def save_metadata(
        self,
        *,
        conversation: ConversationContext,
    ) -> None:
        """
        Persist conversation metadata.

        This does not persist messages.
        """

        await self._store.save_conversation(
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

        await self._store.append_messages(
            conversation_id=conversation.conversation_id
            or "",
            messages=[message],
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

        await self._store.append_messages(
            conversation_id=conversation.conversation_id
            or "",
            messages=messages,
        )

    async def update_summary(
        self,
        *,
        conversation: ConversationContext,
        summary: str,
    ) -> None:
        """
        Update the persisted conversation summary.

        Messages are not modified.
        """

        conversation.summary = summary

        await self.save_metadata(
            conversation=conversation,
        )

    async def clear(
        self,
        *,
        conversation: ConversationContext,
    ) -> None:
        """
        Remove a conversation from storage and
        reset the runtime context.
        """

        conversation_id = (
            conversation.conversation_id
        )

        if conversation_id is not None:

            await self._store.delete_messages(
                conversation_id=conversation_id,
            )

            await self._store.delete_conversation(
                conversation_id=conversation_id,
            )

        conversation.messages.clear()
        conversation.summary = None
        conversation.metadata.clear()
