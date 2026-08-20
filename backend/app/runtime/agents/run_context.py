from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.runtime.chat.message import ChatMessage
from app.runtime.conversation.context import (
    ConversationContext,
)
from app.runtime.events.emitter import Emitter

if TYPE_CHECKING:
    from .agent import Agent
    from .session import AgentSession


@dataclass(slots=True)
class RunContext:
    """
    Context shared across a single execution of an AgentSession.

    RunContext contains only data related to the current
    execution. It does not contain the full conversation
    history, retrieved memories, or retrieved knowledge.

    ContextMonitor performs the approximate token count when
    messages are added. The resulting count is stored here
    so the optimization stage can reuse it without counting
    the context again.
    """

    session: AgentSession

    user_request: str = ""

    emitter: Emitter | None = None

    _messages: list[ChatMessage] = field(
        default_factory=list,
    )

    _context_tokens: int = 0

    _context_threshold_reached: bool = False

    def refresh_context_threshold(
        self,
        *,
        stable_messages: list[ChatMessage] | None = None,
    ) -> None:

        self._context_tokens = (
            self.session.context_monitor.count(
                conversation_context=(
                    self.conversation_context
                ),
                run_context=self,
                stable_messages=stable_messages,
            )
        )

        self._context_threshold_reached = (
            self._context_tokens
            >= self.session.context_monitor.threshold
        )

    def update_context_tokens(
        self,
        tokens: int,
    ) -> None:
        """
        Update the latest approximate context token count.

        This is used after an optimization pass when the
        ContextMonitor measures the modified conversation.
        """

        self._context_tokens = max(
            0,
            tokens,
        )

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
    def context_tokens(
        self,
    ) -> int:
        """
        Most recent approximate context token count.

        This value is calculated by ContextMonitor and reused
        by the optimization stage.
        """

        return self._context_tokens

    @property
    def context_threshold_reached(
        self,
    ) -> bool:
        """
        Whether the approximate context size has reached
        the configured optimization threshold.

        This represents the current threshold-crossing state.

        Once an optimization phase has completed, the state
        is reset so a future message can trigger another
        optimization phase.
        """

        return self._context_threshold_reached

    @property
    def current_user_message(
        self,
    ) -> ChatMessage | None:
        """
        The current user message.
        """

        for message in self._messages:

            if (
                message.role == "user"
                or getattr(
                    message.role,
                    "value",
                    None,
                ) == "user"
            ):
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

            if (
                message.role == "assistant"
                or getattr(
                    message.role,
                    "value",
                    None,
                ) == "assistant"
            ):
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
        Persisted conversation context available to
        the current execution.
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
        Add one message to the current execution.

        After the message is added, perform one approximate
        context measurement.

        No prompt is built and no optimization is performed.
        """

        self._messages.append(
            message,
        )

        self._check_context_threshold()

    def add_messages(
        self,
        messages: list[ChatMessage],
    ) -> None:
        """
        Add multiple messages to the current execution.

        The context is measured once after all messages
        have been added.
        """

        if not messages:
            return

        self._messages.extend(
            messages,
        )

        self._check_context_threshold()

    def _check_context_threshold(
        self,
    ) -> None:
        """
        Perform one approximate context measurement.

        The resulting token count is stored and reused by
        the optimization stage.

        Once the threshold has been reached, additional
        messages do not trigger another measurement until
        the optimization phase explicitly resets the
        threshold state.
        """

        if self._context_threshold_reached:
            return

        self._context_tokens = (
            self.session.context_monitor.count(
                conversation_context=(
                    self.conversation_context
                ),
                run_context=self,
            )
        )

        self._context_threshold_reached = (
            self._context_tokens
            >= self.session.context_monitor.threshold
        )

    def mark_context_optimized(
        self,
        tokens: int,
    ) -> None:
        """
        Mark the current optimization phase as completed.

        The latest measured token count is preserved.

        Only the threshold trigger is reset. This allows the
        next user message to perform a fresh threshold check
        and trigger another optimization phase if necessary.

        Example
        -------
        Before optimization:

            context_tokens = 36000
            threshold_reached = True

        After optimization:

            context_tokens = 3000
            threshold_reached = False

        The next message can therefore establish a new
        threshold-crossing event.
        """

        self.update_context_tokens(
            tokens,
        )

        self._context_threshold_reached = False

    def reset_context_threshold(
        self,
    ) -> None:
        """
        Reset only the threshold trigger.

        The latest context token measurement is preserved.

        This method is kept as a lower-level reset for callers
        that only need to clear the trigger state.
        """

        self._context_threshold_reached = False

    def clear(
        self,
    ) -> None:
        """
        Reset the current execution.
        """

        self._messages.clear()

        self.user_request = ""

        self._context_tokens = 0

        self._context_threshold_reached = False

    def start(
        self,
        user_message: ChatMessage,
    ) -> None:
        """
        Begin a new execution.
        """

        saved_request = self.user_request
        self.clear()

        self.user_request = (
            saved_request or user_message.content
        )

        self.add_message(
            user_message,
        )
