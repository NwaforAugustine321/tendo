from __future__ import annotations

from typing import Any, TYPE_CHECKING

from app.runtime.llm.llm import LLM
from app.runtime.toolsets.tool_context import ToolContext
from app.runtime.agents.middleware import MiddlewareManager, AgentMiddleware
from app.runtime.guardrails.manager import GuardrailManager
from app.runtime.prompts.template import PromptTemplate
from app.runtime.prompts.default_template import DefaultPromptTemplate

if TYPE_CHECKING:
    from .session import AgentSession
    from .runner import AgentRunner


class Agent:
    """
    Immutable Agent configuration.

    An Agent describes HOW an assistant behaves.

    It owns:

    - LLM
    - Instructions
    - ToolContext
    - Metadata
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
    ) -> None:

        self._name = name
        self._description = description
        self._middleware = MiddlewareManager(
            middleware,
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

        self._instructions = instructions

        self._llm = llm
        self._tool_context = ToolContext.from_tools(
            tools,
        )
        self._metadata = metadata or {}

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
    ) -> list[AgentMiddleware]:
        return self._middleware

    @property
    def tool_proxy(
        self,
    ) -> ToolProxyToolset:
        return self._tool_context.proxy

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def instructions(self) -> str:
        return self._instructions

    @property
    def llm(self) -> LLM:
        return self._llm

    @property
    def tool_context(self) -> ToolContext:
        return self._tool_context

    @property
    def metadata(self) -> dict[str, Any]:
        return self._metadata

    @property
    def runner(self) -> AgentRunner:
        """Lazily create an AgentRunner bound to this agent's tool context."""
        if not hasattr(self, "_runner"):
            from .runner import AgentRunner
            from app.runtime.toolsets.executor import ToolExecutor
            proxy = self._tool_context.proxy
            executor = ToolExecutor(proxy)
            self._runner = AgentRunner(tool_executor=executor)
        return self._runner

    def create_session(
        self,
    ) -> AgentSession:
        """
        Create a new conversation session.
        """
        from .session import AgentSession

        return AgentSession(
            agent=self,
        )
