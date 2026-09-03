
from __future__ import annotations

from uuid import uuid4

from app.runtime.chat.message import ChatMessage

from app.runtime.context_manager.default_monitor import (
    DefaultContextMonitor,
)

from app.runtime.context_manager.monitor import (
    ContextMonitor,
)

from app.runtime.prompts.sections.user_task import (
    UserTaskPromptBuilder,
)

from app.runtime.conversation.context import (
    ConversationContext,
)

from app.runtime.events.default_emitter import (
    DefaultEmitter,
)

from app.runtime.events.emitter import (
    Emitter,
)

from app.runtime.llm.response import LLMResponse

from app.runtime.prompts.context import (
    PromptState,
)

from app.runtime.presence_tracker.manager import (
    PresenceTracker,
)

from .activity import AgentActivity

from .agent import Agent

from .run_context import RunContext

from app.runtime.events.events import (
    EventType,
    Status,
    StatusEvent,
)

from app.lib.i18n import I18N


class AgentSession:

    def __init__(
        self,
        *,
        agent: Agent,
        i18n: I18N,
        max_iteration: int,
        max_reasoning_step: int,
        session_id: str | None = None,
        conversation_context: ConversationContext | None = None,
        emitter: Emitter | None = None,
        context_monitor: ContextMonitor | None = None,
        presence_tracker: PresenceTracker | None = None,
    ) -> None:
        self._id = (
            session_id
            or str(uuid4())
        )

        self._agent = agent

        self._conversation_context = (
            conversation_context
            if conversation_context is not None
            else ConversationContext(
                conversation_id=self._id,
            )
        )

        self._emitter = (
            emitter
            if emitter is not None
            else DefaultEmitter()
        )

        self._context_monitor = (
            context_monitor
            if context_monitor is not None
            else DefaultContextMonitor(
                threshold=15000,
            )
        )

        self._prompt_state = PromptState()

        self._presence_tracker = presence_tracker
        self._i18n = i18n
        self._max_iteration = max_iteration
        self._max_reasoning_step = max_reasoning_step

        self._run_context = RunContext(
            session=self,
            emitter=self.emitter,
            max_iteration=max_iteration,
            max_reasoning_step=max_reasoning_step,
            i18n=i18n,
            presence_tracker=self._presence_tracker,
        )

        self._user_task_builder = UserTaskPromptBuilder()

        self._current_activity: AgentActivity | None = None

    @property
    def id(
        self,
    ) -> str:
        return self._id

    @property
    def agent(
        self,
    ) -> Agent:
        return self._agent

    @property
    def conversation_context(
        self,
    ) -> ConversationContext:
        return self._conversation_context

    @property
    def run_context(
        self,
    ) -> RunContext:
        return self._run_context

    @property
    def emitter(
        self,
    ) -> Emitter:
        return self._emitter

    @property
    def context_monitor(
        self,
    ) -> ContextMonitor:
        return self._context_monitor

    @property
    def prompt_state(
        self,
    ) -> PromptState:
        return self._prompt_state

    @property
    def presence_tracker(
        self,
    ) -> PresenceTracker | None:
        return self._presence_tracker

    @property
    def current_activity(
        self,
    ) -> AgentActivity | None:
        return self._current_activity

    @property
    def running(
        self,
    ) -> bool:
        return (
            self._current_activity is not None
            and not self._current_activity.finished
        )

    async def run(
        self,
        message: str,
    ) -> LLMResponse:
        self._run_context.user_request = message

        request = self._user_task_builder.build(message)

        return await self.run_message(
            ChatMessage.user(
                request
            )
        )

    async def run_message(
        self,
        message: ChatMessage,
    ) -> LLMResponse:
        if self._agent.conversation is not None:
            loaded = await (
                self._agent.conversation.load(
                    conversation_id=(
                        self._conversation_context.conversation_id
                        or self._id
                    ),
                )
            )

            self._conversation_context = loaded

        self._run_context.start(
            message,
        )

        runner = self._agent.create_runner(
            self._run_context,
        )

        return await runner.run(
            self,
        )

    def set_current_activity(
        self,
        activity: AgentActivity,
    ) -> None:
        self._current_activity = activity

    def clear_activity(
        self,
    ) -> None:
        self._current_activity = None

    def reset(
        self,
    ) -> None:
        self._conversation_context = (
            ConversationContext(
                conversation_id=self.id,
            )
        )

        self._prompt_state = PromptState()

        self._run_context = RunContext(
            session=self,
            emitter=self.emitter,
            max_iteration=self._max_iteration,
            max_reasoning_step=self._max_reasoning_step,
            i18n=self._i18n,
            presence_tracker=self._presence_tracker,
        )

        self._current_activity = None

    async def aclose(
        self,
    ) -> None:
        if self._current_activity is not None:
            await self._current_activity.cancel()

        self._current_activity = None

        if self._presence_tracker is not None:
            await self._presence_tracker.aclose()
