from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from app.runtime.chat.context import ChatContext
from app.runtime.chat.message import ChatMessage

if TYPE_CHECKING:
    from .agent import Agent
    from .session import AgentSession


@dataclass(slots=True)
class RunContext:
    """
    Context shared across a single execution of an AgentSession.

    RunContext provides convenient access to the current
    AgentSession while also tracking the messages generated
    during the current run.

    ChatContext contains the entire conversation.

    RunContext only contains the messages produced during
    the current execution, making it suitable for reflection,
    memory extraction, analytics, and learning.
    """

    session: AgentSession

    _run_messages: list[ChatMessage] = field(
        default_factory=list,
    )

    @property
    def current_messages(
        self,
    ) -> list[ChatMessage]:
        """
        Messages generated during the current execution.
        """
        return list(self._run_messages)

    @property
    def current_conversation(
        self,
    ) -> str:
        """
        Current execution formatted as a conversation.
        """

        return "\n".join(
            f"{message.role}: {message.content}"
            for message in self._run_messages
        )

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
    def chat_context(
        self,
    ) -> ChatContext:
        """
        Complete conversation history.
        """
        return self.session.chat_context

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

    def add_current_message(
        self,
        message: ChatMessage,
    ) -> None:
        """
        Add a message to the current execution.
        """

        self._run_messages.append(
            message,
        )

    def add_current_messages(
        self,
        messages: list[ChatMessage],
    ) -> None:
        """
        Add multiple messages to the current execution.
        """

        self._run_messages.extend(
            messages,
        )

    def clear_current_messages(
        self,
    ) -> None:
        """
        Reset the current execution transcript.
        """

        self._run_messages.clear()

    def start_run(
        self,
        user_message: ChatMessage,
    ) -> None:
        """
        Begin a new execution.
        """

        self.clear_current_messages()

        self.add_current_message(
            user_message,
        )
