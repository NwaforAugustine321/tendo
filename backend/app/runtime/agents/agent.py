from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.runtime.context_manager.manager import (
    ContextManager,
)
from app.runtime.conversation.provider import (
    ConversationProvider,
)
from app.runtime.events.emitter import (
    Emitter,
)
from app.runtime.guardrails.manager import (
    GuardrailManager,
)
from app.runtime.llm.llm import (
    LLM,
)
from app.runtime.memory.provider import (
    MemoryProvider,
)
from app.runtime.middlewares.middleware import (
    AgentMiddleware,
    MiddlewareManager,
)
from app.runtime.prompts.default_template import (
    DefaultPromptTemplate,
)
from app.runtime.prompts.template import (
    PromptTemplate,
)
from app.runtime.rag.provider import (
    RAGProvider,
)
from app.runtime.toolsets.tool_context import (
    ToolContext,
)

from ..tools.default import (
    create_memory_tool,
    create_rag_tool,
)

if TYPE_CHECKING:
    from .runner import AgentRunner
    from .session import AgentSession


class Agent:
    """
    Immutable Agent configuration.

    An Agent describes HOW an assistant behaves.

    It owns:

    - LLM
    - Prompt template
    - Context manager
    - Memory
    - Conversation
    - RAG
    - Middleware
    - Guardrails
    - Tool context
    """

    def __init__(
        self,
        *,
        name: str,
        llm: LLM,
        instructions: str = "",
        tools: list[Any] | None = None,
        description: str = "",
        output_type: type | None = None,
        metadata: dict[str, Any] | None = None,
        middleware: list[AgentMiddleware] | None = None,
        guardrails: GuardrailManager | None = None,
        prompt_template: PromptTemplate | None = None,
        context_manager: ContextManager | None = None,
        memory: MemoryProvider | None = None,
        conversation: ConversationProvider | None = None,
        rag: RAGProvider | None = None,
        max_iteration: int = 6,
        max_reasoning_steps: int = 2,
        enable_runtime_rag_mem: bool | None = False
    ) -> None:

        self._name = name
        self._description = description
        self._instructions = instructions

        self._llm = llm

        self._memory = memory
        self._conversation = conversation
        self._rag = rag
        self._max_iterations = max_iteration
        self._max_reasoning_steps = max_reasoning_steps
        self._enable_runtime_rag_mem = enable_runtime_rag_mem

        self._tools = list(
            tools or [],
        )

        runtime_tools = [
            *self._tools,
        ]

        if self._memory is not None:

            runtime_tools.append(
                create_memory_tool(
                    agent=self,
                ),
            )

        if self._rag is not None:

            runtime_tools.append(
                create_rag_tool(
                    agent=self,
                ),
            )

        #
        # Create ToolContext once.
        #

        self._tool_context = ToolContext.from_tools(
            runtime_tools,
        )

        self._metadata = metadata or {}

        self._output_type = output_type

        #
        # Prepare the LLM once.
        #

        self._llm.prepare(
            tool_context=self._tool_context,
            output_type=self._output_type,
        )

        self._guardrails = (
            guardrails
            if guardrails is not None
            else GuardrailManager()
        )

        self._prompt_template = (
            prompt_template
            if prompt_template is not None
            else DefaultPromptTemplate()
        )

        self._context_manager = (
            context_manager
            if context_manager is not None
            else ContextManager()
        )

        self._middleware = MiddlewareManager()

        if middleware:

            self._middleware.extend(
                middleware,
            )

        if self._conversation is not None:

            self._middleware.extend(
                self._conversation.middleware(),
            )

        if self._memory is not None:

            self._middleware.extend(
                self._memory.middleware(),
            )

    @property
    def name(
        self,
    ) -> str:

        return self._name

    @property
    def description(
        self,
    ) -> str:

        return self._description

    @property
    def instructions(
        self,
    ) -> str:

        return self._instructions

    @property
    def llm(
        self,
    ) -> LLM:

        return self._llm

    @property
    def context_manager(
        self,
    ) -> ContextManager:

        return self._context_manager

    @property
    def memory(
        self,
    ) -> MemoryProvider | None:

        return self._memory

    @property
    def conversation(
        self,
    ) -> ConversationProvider | None:

        return self._conversation

    @property
    def rag(
        self,
    ) -> RAGProvider | None:

        return self._rag

    @property
    def guardrails(
        self,
    ) -> GuardrailManager:

        return self._guardrails

    @property
    def prompt_template(
        self,
    ) -> PromptTemplate:

        return self._prompt_template

    @property
    def middleware(
        self,
    ) -> MiddlewareManager:

        return self._middleware

    @property
    def tool_context(
        self,
    ) -> ToolContext:

        return self._tool_context

    @property
    def metadata(
        self,
    ) -> dict[str, Any]:

        return self._metadata

    @property
    def output_type(
        self,
    ) -> type | None:

        return self._output_type

    def create_runner(
        self,
        run_context: RunContext,
    ) -> AgentRunner:
        """
        Create a runner for the current execution.

        Tools are owned by the Agent and ToolContext.
        RunContext is supplied only to the execution layer.
        """

        from app.runtime.toolsets.executor import (
            ToolExecutor,
        )
        from .runner import AgentRunner

        return AgentRunner(
            tool_executor=ToolExecutor(
                self._tool_context.proxy,
                run_context=run_context,
            ),
            max_iterations=self._max_iterations,
            max_reasoning_steps=self._max_reasoning_steps
        )

    @property
    def runner(
        self,
    ) -> AgentRunner:
        """
        Lazily create the static runner.

        This runner is retained for callers that do not require
        runtime-dependent execution context.
        """

        if not hasattr(
            self,
            "_runner",
        ):

            from app.runtime.toolsets.executor import (
                ToolExecutor,
            )
            from .runner import AgentRunner

            self._runner = AgentRunner(
                tool_executor=ToolExecutor(
                    self._tool_context.proxy,
                ),
                max_iterations=self._max_iterations,
                max_reasoning_steps=self._max_reasoning_steps
            )

        return self._runner

    def create_session(
        self,
        session_id: str | None = None,
        emitter: Emitter | None = None,
    ) -> AgentSession:
        """
        Create a new conversation session.
        """

        from .session import AgentSession

        return AgentSession(
            agent=self,
            session_id=session_id,
            emitter=emitter,
            enable_runtime_rag_mem=self._enable_runtime_rag_mem
        )
