from __future__ import annotations

from typing import Any, TYPE_CHECKING

from app.runtime.middlewares.middleware import (
    AgentMiddleware,
    MiddlewareManager,
)
from app.runtime.rag.provider import (
    RAGProvider,
)
from app.runtime.conversation.provider import (
    ConversationProvider,
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
from app.runtime.prompts.default_template import (
    DefaultPromptTemplate,
)
from app.runtime.prompts.template import (
    PromptTemplate,
)
from app.runtime.toolsets.tool_context import (
    ToolContext,
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
    - Memory
    - Conversation
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
        memory: MemoryProvider | None = None,
        conversation: ConversationProvider | None = None,
        rag: RAGProvider | None = None,
    ) -> None:

        self._name = name
        self._description = description
        self._instructions = instructions

        self._llm = llm

        self._memory = memory
        self._conversation = conversation
        self._rag = rag

        self._tool_context = ToolContext.from_tools(
            tools,
        )

        self._metadata = metadata or {}

        self._output_type = output_type

        self._guardrails = (
            guardrails
            if guardrails is not None
            else GuardrailManager()
        )

        self._prompt_template = DefaultPromptTemplate()

        self._middleware = MiddlewareManager()

        #
        # User supplied middleware.
        #
        if middleware:
            self._middleware.extend(
                middleware,
            )

        #
        # Provider middleware.
        #
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
    def runner(
        self,
    ) -> AgentRunner:
        """
        Lazily create the runner.
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
            )

        return self._runner

    def create_session(
        self,
        session_id: str | None = None,
    ) -> AgentSession:
        """
        Create a new conversation session.
        """

        from .session import AgentSession

        return AgentSession(
            agent=self,
            session_id=session_id,
        )
