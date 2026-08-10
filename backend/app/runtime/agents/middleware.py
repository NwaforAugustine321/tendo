from __future__ import annotations
from typing import Any

from abc import ABC

from enum import Enum

from app.runtime.llm.response import LLMResponse
from app.runtime.toolsets.executor import ToolExecutionResult

from .run_context import RunContext


class MiddlewareEvent(str, Enum):
    BEFORE_RUN = "before_run"
    AFTER_RUN = "after_run"

    BEFORE_LLM = "before_llm"
    AFTER_LLM = "after_llm"

    BEFORE_TOOLS = "before_tools"
    AFTER_TOOLS = "after_tools"

    ON_ERROR = "on_error"


class AgentMiddleware(ABC):
    """
    Base class for Agent middleware.

    Every lifecycle method is optional.
    """

    async def before_run(
        self,
        ctx: RunContext,
    ) -> None:
        pass

    async def after_run(
        self,
        ctx: RunContext,
        response: LLMResponse,
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
        response: LLMResponse | None,
    ) -> None:
        pass

    async def before_tools(
        self,
        ctx: RunContext,
        tool_calls: Any
    ) -> None:
        pass

    async def after_tools(
        self,
        ctx: RunContext,
        results: list[ToolExecutionResult],
    ) -> None:
        pass

    async def on_error(
        self,
        ctx: RunContext,
        error: Exception,
    ) -> None:
        pass


class MiddlewareManager:
    """
    Dispatches middleware lifecycle events.
    """

    def __init__(
        self,
        middleware: list[AgentMiddleware] | None = None,
    ) -> None:

        self._middleware = middleware or []

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
        *args: Any,
    ) -> list[Any]:
        """
        Dispatch a lifecycle event to every middleware.

        Returns every middleware result in execution order.
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

            results.append(
                await handler(
                    *args,
                )
            )

        return results
