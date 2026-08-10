from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.runtime.chat.message import ChatMessage
from app.runtime.llm.response import LLMResponse
from app.runtime.toolsets.executor import ToolExecutionResult

from app.runtime.agents.run_context import RunContext


class MiddlewareEvent(StrEnum):
    BEFORE_RUN = "before_run"
    AFTER_RUN = "after_run"

    BEFORE_LLM = "before_llm"
    AFTER_LLM = "after_llm"

    BEFORE_TOOLS = "before_tools"
    AFTER_TOOLS = "after_tools"

    ON_ERROR = "on_error"


#
# ------------------------------------------------------------------
# Event payloads
# ------------------------------------------------------------------
#

@dataclass(slots=True)
class AfterLLMEvent:

    message: ChatMessage

    response: LLMResponse


@dataclass(slots=True)
class BeforeToolsEvent:

    tool_calls: Any


@dataclass(slots=True)
class AfterToolsEvent:

    messages: list[ChatMessage]

    results: list[ToolExecutionResult]


@dataclass(slots=True)
class ErrorEvent:

    error: Exception


@dataclass(slots=True)
class AfterRunEvent:

    response: LLMResponse | None


#
# ------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------
#

class AgentMiddleware(ABC):
    """
    Base class for Agent middleware.

    Every lifecycle hook is optional.
    """

    async def before_run(
        self,
        ctx: RunContext,
    ) -> None:
        pass

    async def after_run(
        self,
        ctx: RunContext,
        event: AfterRunEvent,
    ) -> None:
        pass

    async def before_llm(
        self,
        ctx: RunContext,
    ) -> None:
        pass

    async def after_llm(
        self,
        ctx: RunContext,
        event: AfterLLMEvent,
    ) -> None:
        pass

    async def before_tools(
        self,
        ctx: RunContext,
        event: BeforeToolsEvent,
    ) -> None:
        pass

    async def after_tools(
        self,
        ctx: RunContext,
        event: AfterToolsEvent,
    ) -> None:
        pass

    async def on_error(
        self,
        ctx: RunContext,
        event: ErrorEvent,
    ) -> None:
        pass


#
# ------------------------------------------------------------------
# Manager
# ------------------------------------------------------------------
#

class MiddlewareManager:
    """
    Dispatches middleware lifecycle events.
    """

    def __init__(
        self,
        middleware: list[AgentMiddleware] | None = None,
    ) -> None:

        self._middleware = middleware or []

    @property
    def middleware(
        self,
    ) -> list[AgentMiddleware]:

        return list(
            self._middleware,
        )

    def add(
        self,
        middleware: AgentMiddleware,
    ) -> None:

        self._middleware.append(
            middleware,
        )

    def extend(
        self,
        middleware: list[AgentMiddleware],
    ) -> None:

        self._middleware.extend(
            middleware,
        )

    async def dispatch(
        self,
        event: MiddlewareEvent,
        ctx: RunContext,
        payload: Any = None,
    ) -> list[Any]:
        """
        Dispatch a lifecycle event to every middleware.
        """

        results: list[Any] = []

        for middleware in self._middleware:

            handler = getattr(
                middleware,
                event.value,
                None,
            )

            if handler is None:
                continue

            if payload is None:

                result = await handler(
                    ctx,
                )

            else:

                result = await handler(
                    ctx,
                    payload,
                )

            results.append(
                result,
            )

        return results
