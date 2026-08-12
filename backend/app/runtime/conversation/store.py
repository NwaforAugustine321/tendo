from __future__ import annotations

from abc import ABC, abstractmethod

from app.runtime.chat.message import ChatMessage

from .context import ConversationContext


class ConversationStore(ABC):
    """
    Persistent storage for conversations.

    A conversation consists of two independent parts:

    - Conversation metadata
      (summary, metadata, state, etc.)

    - Conversation messages
      (append-only message history)

    This separation allows conversation summarization
    without rewriting the entire conversation history.
    """

    @abstractmethod
    async def save_conversation(
        self,
        *,
        conversation: ConversationContext,
    ) -> None:
        """
        Create or update the conversation metadata.
        """
        ...

    @abstractmethod
    async def load_conversation(
        self,
        *,
        conversation_id: str,
    ) -> ConversationContext | None:
        """
        Load conversation metadata.

        Does not load conversation messages.
        """
        ...

    @abstractmethod
    async def find_all(
        self,
    ) -> list[ConversationContext]:
        """
        Return all conversation metadata.
        """
        ...

    @abstractmethod
    async def delete_conversation(
        self,
        *,
        conversation_id: str,
    ) -> None:
        """
        Delete a conversation and all of its messages.
        """
        ...

    #
    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------
    #

    @abstractmethod
    async def append_messages(
        self,
        *,
        conversation_id: str,
        messages: list[ChatMessage],
    ) -> None:
        """
        Append new messages to a conversation.

        Existing messages must never be rewritten.
        """
        ...

    @abstractmethod
    async def load_messages(
        self,
        *,
        conversation_id: str,
        limit: int | None = None,
    ) -> list[ChatMessage]:
        """
        Load conversation messages.

        Returns the most recent messages when
        a limit is supplied.
        """
        ...

    @abstractmethod
    async def delete_messages(
        self,
        *,
        conversation_id: str,
        before_message_id: str | None = None,
    ) -> None:
        """
        Delete conversation messages.

        When ``before_message_id`` is provided,
        delete only messages before that message.

        When omitted, delete all messages.
        """
        ...
