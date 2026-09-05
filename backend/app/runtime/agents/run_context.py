from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.runtime.chat.message import ChatMessage
from app.runtime.conversation.context import ConversationContext
from app.runtime.events.emitter import Emitter
from app.lib.i18n import I18N
from app.runtime.presence_tracker.interface import PresenceResult
from app.runtime.presence_tracker.manager import PresenceTracker
from app.runtime.response_queue.queue import ResponseQueue
from app.runtime.events.events import (
    StatusEvent,
)

if TYPE_CHECKING:
    from .agent import Agent
    from .session import AgentSession


@dataclass(slots=True)
class RunContext:

    session: AgentSession
    i18n: I18N
    max_iteration: int
    max_reasoning_step: int
    user_request: str = ""
    emitter: Emitter | None = None
    presence_tracker: PresenceTracker | None = None
    response_queue: ResponseQueue | None = None

    _messages: list[ChatMessage] = field(
        default_factory=list,
    )

    _context_tokens: int = 0
    _context_threshold_reached: bool = False

    async def presence_classify(
        self,
    ) -> PresenceResult | None:

        tracker = self.presence_tracker

        if tracker is None:
            return None

        return await tracker.classify()

    async def presence_state(
        self,
        *,
        event: StatusEvent,
        iteration: int = 0,
    ) -> None:

        status = event.status

        tracker = self.presence_tracker

        if tracker is None:
            return

        state = tracker.state

        if state is None:
            return

        state.status = status.value
        state.stage = status.value
        state.iteration = iteration

        tracker.notify_state_event(
            state=state.snapshot(),
        )

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
        self._context_tokens = max(
            0,
            tokens,
        )

    @property
    def messages(
        self,
    ) -> list[ChatMessage]:
        return list(
            self._messages,
        )

    @property
    def context_tokens(
        self,
    ) -> int:
        return self._context_tokens

    @property
    def context_threshold_reached(
        self,
    ) -> bool:
        return self._context_threshold_reached

    @property
    def current_user_message(
        self,
    ) -> ChatMessage | None:
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
        return "\n".join(
            f"{message.role}: {message.content}"
            for message in self._messages
        )

    @property
    def conversation_context(
        self,
    ) -> ConversationContext:
        return self.session.conversation_context

    @property
    def conversation_id(
        self,
    ) -> str | None:
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
        return self.agent.guardrails

    @property
    def agent(
        self,
    ) -> Agent:
        return self.session.agent

    @property
    def session_id(
        self,
    ) -> str:
        return self.session.id

    @property
    def metadata(
        self,
    ) -> dict[str, Any]:
        return {}

    def add_message(
        self,
        message: ChatMessage,
    ) -> None:
        self._messages.append(
            message,
        )

        self._check_context_threshold()

    def add_messages(
        self,
        messages: list[ChatMessage],
    ) -> None:
        if not messages:
            return

        self._messages.extend(
            messages,
        )

        self._check_context_threshold()

    def _check_context_threshold(
        self,
    ) -> None:
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
        self.update_context_tokens(
            tokens,
        )

        self._context_threshold_reached = False

    def reset_context_threshold(
        self,
    ) -> None:
        self._context_threshold_reached = False

    def clear(
        self,
    ) -> None:
        self._messages.clear()
        self.user_request = ""
        self._context_tokens = 0
        self._context_threshold_reached = False

    def start(
        self,
        user_message: ChatMessage,
    ) -> None:
        saved_request = self.user_request

        self.clear()

        self.user_request = (
            saved_request or user_message.content
        )

        self.add_message(
            user_message,
        )
