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
    - Load conversation metadata.
    - Load conversation messages.
    - Assemble the runtime conversation.
    - Persist summaries.
    - Append messages.
    - Delete messages.
    - Reload runtime state.
    - Delegate conversation optimization.
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

    @property
    def store(
        self,
    ) -> ConversationStore:
        return self._store

    async def optimize(
        self,
        *,
        conversation: ConversationContext,
        current_tokens: int,
        target_tokens: int,
    ) -> OptimizationResult:
        """
        Attempt to reduce the conversation's
        contribution to the prompt.
        """

        return await self._optimizer.optimize(
            conversation=conversation,
            current_tokens=current_tokens,
            target_tokens=target_tokens,
        )

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

        Metadata and persisted messages are loaded
        independently and assembled into the runtime
        ConversationContext.
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

        messages = await self._store.load_messages(
            conversation_id=conversation_id,
            limit=message_limit,
        )

        #
        # Inject the persisted rolling summary
        # as a runtime system message.
        #
        if conversation.summary:

            conversation.messages = [
                ChatMessage.summary(
                    conversation.summary,
                ),
                *messages,
            ]

        else:

            conversation.messages = messages

        return conversation

    async def reload(
        self,
        *,
        conversation: ConversationContext,
        message_limit: int | None = None,
    ) -> None:
        """
        Reload the runtime conversation from storage.
        """

        if conversation.conversation_id is None:
            return

        refreshed = await self.load(
            conversation_id=conversation.conversation_id,
            message_limit=message_limit,
        )

        conversation.summary = refreshed.summary
        conversation.messages = refreshed.messages
        conversation.metadata = refreshed.metadata
        conversation.state = refreshed.state

    async def save_metadata(
        self,
        *,
        conversation: ConversationContext,
    ) -> None:
        """
        Persist conversation metadata.
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

    async def delete_messages(
        self,
        *,
        conversation: ConversationContext,
        messages: list[ChatMessage],
    ) -> None:
        """
        Delete persisted messages.
        """

        if (
            conversation.conversation_id is None
            or not messages
        ):
            return

        message_ids = [
            message.message_id
            for message in messages
            if message.message_id is not None
        ]

        if not message_ids:
            return

        await self._store.delete_messages(
            conversation_id=conversation.conversation_id,
            message_ids=message_ids,
        )

    async def update_summary(
        self,
        *,
        conversation: ConversationContext,
        summary: str,
    ) -> None:
        """
        Persist the rolling conversation summary.
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
        Delete an entire conversation.
        """

        if conversation.conversation_id is not None:

            await self._store.delete_messages(
                conversation_id=conversation.conversation_id,
            )

            await self._store.delete_conversation(
                conversation_id=conversation.conversation_id,
            )

        conversation.messages.clear()
        conversation.summary = None
        conversation.metadata.clear()
