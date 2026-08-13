from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.runtime.chat.message import ChatMessage
from app.runtime.conversation.context import (
    ConversationContext,
)

if TYPE_CHECKING:
    from .agent import Agent
    from .session import AgentSession
from app.runtime.events.emitter import Emitter
from app.runtime.events.default_emitter import DefaultEmitter
from app.runtime.events.default_emitter import DefaultEmitter


@dataclass(slots=True)
class RunContext:
    """
    Context shared across a single execution of an AgentSession.

    RunContext contains only data related to the current
    execution. It does not contain the full conversation
    history, retrieved memories, or retrieved knowledge.
    """

    session: AgentSession

    user_request: str = ""

    _messages: list[ChatMessage] = field(
        default_factory=list,
    )

    emitter: Emitter

    @property
    def emitter(self) -> Emitter:
        return self.emitter

    @property
    def messages(
        self,
    ) -> list[ChatMessage]:
        """
        Messages produced during the current execution.
        """

        return list(
            self._messages,
        )

    @property
    def current_user_message(
        self,
    ) -> ChatMessage | None:
        """
        The current user message.
        """

        for message in self._messages:

            if message.role == "user" or getattr(
                message.role,
                "value",
                None,
            ) == "user":
                return message

        return None

    @property
    def current_assistant_message(
        self,
    ) -> ChatMessage | None:
        """
        The latest assistant message produced during
        this execution.
        """

        for message in reversed(
            self._messages,
        ):

            if message.role == "assistant" or getattr(
                message.role,
                "value",
                None,
            ) == "assistant":
                return message

        return None

    @property
    def conversation(
        self,
    ) -> str:
        """
        Current execution formatted as a conversation.
        """

        return "\n".join(
            f"{message.role}: {message.content}"
            for message in self._messages
        )

    @property
    def conversation_context(
        self,
    ) -> ConversationContext:
        """
        Previously persisted conversation.
        """

        return self.session.conversation_context

    @property
    def conversation_id(
        self,
    ) -> str | None:
        """
        Current conversation identifier.
        """

        return self.conversation_context.conversation_id

    @property
    def middleware(
        self,
    ):
        return self.agent.middleware

    @property
    def guardrails(
        self,
    ):
        """
        Agent guardrail manager.
        """

        return self.agent.guardrails

    @property
    def agent(
        self,
    ) -> Agent:
        """
        The executing agent.
        """

        return self.session.agent

    @property
    def session_id(
        self,
    ) -> str:
        """
        Unique session identifier.
        """

        return self.session.id

    @property
    def metadata(
        self,
    ) -> dict[str, Any]:
        """
        Optional runtime metadata.
        """

        return {}

    def add_message(
        self,
        message: ChatMessage,
    ) -> None:
        """
        Add a message to the current execution.
        """

        self._messages.append(
            message,
        )

    def add_messages(
        self,
        messages: list[ChatMessage],
    ) -> None:
        """
        Add multiple messages to the current execution.
        """

        self._messages.extend(
            messages,
        )

    def clear(
        self,
    ) -> None:
        """
        Reset the current execution.
        """

        self._messages.clear()

        self.user_request = ""

    def start(
        self,
        user_message: ChatMessage,
    ) -> None:
        """
        Begin a new execution.
        """

        self.clear()

        self.user_request = (
            user_message.content
        )

        self.add_message(
            user_message,
        )
