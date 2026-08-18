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

from .activity import AgentActivity
from .agent import Agent
from .run_context import RunContext
from app.runtime.events.events import (
    EventType,
    Status,
    StatusEvent,
)


class AgentSession:
    """
    Represents one active conversation with an Agent.

    A session owns all mutable runtime state.

    Responsibilities
    ----------------
    - Own the ConversationContext
    - Own the PromptState
    - Own the RunContext
    - Own the ContextMonitor
    - Track the active AgentActivity
    - Execute conversations
    - Manage the lifetime of a conversation
    """

    def __init__(
        self,
        *,
        agent: Agent,
        session_id: str | None = None,
        conversation_context: ConversationContext | None = None,
        emitter: Emitter | None = None,
        context_monitor: ContextMonitor | None = None,
        enable_runtime_rag_mem: bool | None = False
    ) -> None:

        self._id = (
            session_id
            or str(uuid4())
        )

        self._agent = agent
        self._enable_runtime_rag_mem = enable_runtime_rag_mem

        self._conversation_context = (
            conversation_context
            if conversation_context is not None
            else ConversationContext(
                conversation_id=self._id,
            )
        )

        #
        # Session-level emitter.
        #
        # The same emitter is reused for the entire
        # lifetime of this session.
        #
        self._emitter = (
            emitter
            if emitter is not None
            else DefaultEmitter()
        )

        #
        # Session-level context monitor.
        #
        # The monitor is reused for every execution.
        #
        self._context_monitor = (
            context_monitor
            if context_monitor is not None
            else DefaultContextMonitor(
                threshold=10500,
            )
        )

        #
        # Session-level prompt state.
        #
        # This survives across inference calls.
        #
        # It allows the runtime to reuse stable prompt
        # components instead of rebuilding them on every
        # LLM/tool iteration.
        #
        self._prompt_state = PromptState()

        #
        # Per-execution runtime state.
        #
        self._run_context = RunContext(
            session=self,
            emitter=self.emitter,
            enable_runtime_rag_mem=self._enable_runtime_rag_mem
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
        """
        Loaded conversation history.
        """

        return self._conversation_context

    @property
    def run_context(
        self,
    ) -> RunContext:
        """
        Current execution context.
        """

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
        """
        Monitors the approximate context size and
        determines when optimization is required.
        """

        return self._context_monitor

    @property
    def prompt_state(
        self,
    ) -> PromptState:
        """
        Runtime state used to reuse stable prompt
        components across inference calls.
        """

        return self._prompt_state

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
        """
        Execute one conversational turn.
        """

        # main message to save
        self._run_context.user_request = message

        # rebuild with instruction context for runtime
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
        """
        Execute one conversational turn.

        The persisted conversation is loaded before the
        execution starts.

        PromptState is intentionally preserved because it
        belongs to the session rather than to one execution.
        """
        await self._emitter.emit(
            EventType.PROGRESS,
            StatusEvent(
                status=Status.STARTING,
            ),
        )

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
        """
        Reset the session while preserving:

        - session identity
        - emitter
        - context monitor

        Conversation and prompt runtime state are reset
        for a completely fresh session state.
        """

        self._conversation_context = (
            ConversationContext(
                conversation_id=self.id,
            )
        )

        #
        # A full session reset means the previously
        # prepared prompt state is no longer valid.
        #
        self._prompt_state = PromptState()

        self._run_context = RunContext(
            session=self,
            emitter=self.emitter,
        )

        self._current_activity = None

    async def aclose(
        self,
    ) -> None:
        """
        Cancel any running activity.
        """

        if self._current_activity is not None:
            await self._current_activity.cancel()

        self._current_activity = None
