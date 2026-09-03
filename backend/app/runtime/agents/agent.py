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

from app.runtime.guardrails.guards.strategies.strategy import (
    PromptLeakageDetectionMode,
)

from app.runtime.response_queue.interface import (
    ResponseConsumer,
)

from ..tools.default import (
    create_memory_tool,
    create_rag_tool,
)

from app.runtime.guardrails.guards.prompt_leakage_detector import (
    PromptLeakageSafetyGuardrail,
)

from app.runtime.guardrails.guards.strategies.manual_prompt_leakage_detector import (
    ManualPromptLeakageStrategy,
)

from app.runtime.guardrails.guards.strategies.semantic_prompt_leakage_detector import (
    SemanticLeakageSearchStrategy,
)

from app.lib.i18n import (
    _get_i18n,
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
        max_iteration: int = 3,
        max_reasoning_step: int = 2,
        enable_runtime_rag: bool | None = False,
        enable_runtime_mem: bool | None = False,
        enable_self_reflection: bool = True,
        prompt_detector_strategy: PromptLeakageDetectionMode = (
            PromptLeakageDetectionMode.HYBRID
        ),
        response_consumers: list[ResponseConsumer] | None = None,
    ) -> None:

        self._name = name

        self._description = description

        self._instructions = instructions

        self._enable_self_reflection = (
            enable_self_reflection
        )

        self._enable_runtime_mem = (
            enable_runtime_mem
        )

        self._enable_runtime_rag = (
            enable_runtime_rag
        )

        self._prompt_detector_strategy = (
            prompt_detector_strategy
        )

        self._response_consumers = list(
            response_consumers or [],
        )

        self._llm = llm

        self._memory = memory

        self._conversation = conversation

        self._rag = rag

        self._max_iteration = max_iteration

        self._max_reasoning_step = (
            max_reasoning_step
        )

        self._i18n = _get_i18n()

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

        # Create ToolContext once.

        self._tool_context = ToolContext.from_tools(
            runtime_tools,
        )

        self._metadata = metadata or {}

        self._output_type = output_type

        # Prepare the LLM once.

        self._llm.prepare(
            tool_context=self._tool_context,
            output_type=self._output_type,
        )

        self._semantic_leakage_strategy = (
            SemanticLeakageSearchStrategy()
        )

        self._manual_leakage_strategy = (
            ManualPromptLeakageStrategy()
        )

        self._semantic_leakage_strategy.queue_index(
            [
                {
                    "id": "internl.default",
                    "content": self._i18n.get(
                        "slices.governance_policy"
                    ),
                    "source": "internal:[default]",
                },
                {
                    "id": name,
                    "content": instructions,
                    "source": f"agent:[{name}]",
                },
            ]
        )

        self._prompt_guard = (
            PromptLeakageSafetyGuardrail(
                mode=self._prompt_detector_strategy,
                manual=self._manual_leakage_strategy,
                semantic=self._semantic_leakage_strategy,
            )
        )

        self._guardrails = (
            guardrails
            if guardrails is not None
            else GuardrailManager(
                guardrails=[
                    self._prompt_guard,
                ]
            )
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

    @property
    def response_consumers(
        self,
    ) -> list[ResponseConsumer]:

        return self._response_consumers

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
            )
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
                )
            )

        return self._runner

    def create_session(
        self,
        session_id: str | None = None,
        emitter: Emitter | None = None,
    ) -> AgentSession:
        """
        Create a new conversation session.

        The Agent supplies its configured response consumers to the
        session. The AgentSession owns the ResponseQueue and the
        mutable runtime state.
        """

        from .session import AgentSession

        return AgentSession(
            agent=self,
            session_id=session_id,
            emitter=emitter,
            max_iteration=self._max_iteration,
            max_reasoning_step=self._max_reasoning_step,
            i18n=self._i18n,
            response_consumers=self._response_consumers,
        )
