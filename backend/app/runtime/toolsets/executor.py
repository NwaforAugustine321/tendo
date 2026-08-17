from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from app.runtime.agents.run_context import RunContext
from app.runtime.chat.message import ChatMessage
from app.runtime.llm.response import ToolCall
from app.runtime.toolsets.tool_proxy import (
    ToolProxyToolset,
)
from app.runtime.tools.default import (
    reset_run_context,
    set_run_context,
)


@dataclass(
    slots=True,
    frozen=True,
)
class ToolExecutionResult:
    """
    Result of executing a single tool.
    """

    tool_call: ToolCall

    output: Any


class ToolExecutor:
    """
    Executes tools through a ToolProxyToolset.

    The RunContext is runtime state and is injected through
    the execution context rather than being exposed as a
    tool argument to the LLM.
    """

    def __init__(
        self,
        proxy: ToolProxyToolset,
        *,
        run_context: RunContext | None = None,
    ) -> None:
        self._proxy = proxy
        self._run_context = run_context

    @property
    def proxy(
        self,
    ) -> ToolProxyToolset:
        return self._proxy

    @property
    def run_context(
        self,
    ) -> RunContext | None:
        return self._run_context

    async def execute_one(
        self,
        tool_call: ToolCall,
        *,
        ctx: RunContext | None = None,
    ) -> ToolExecutionResult:
        """
        Execute one tool call.

        An explicitly supplied context takes precedence over
        the context bound to this executor.
        """

        context = (
            ctx
            if ctx is not None
            else self._run_context
        )

        token = None

        if context is not None:
            token = set_run_context(
                context,
            )

        try:
            output = await self._proxy.execute(
                name=tool_call.name,
                arguments=tool_call.arguments,
                ctx=context,
            )

            return ToolExecutionResult(
                tool_call=tool_call,
                output=output,
            )

        finally:
            if token is not None:
                reset_run_context(
                    token,
                )

    async def execute(
        self,
        tool_calls: list[ToolCall],
        *,
        ctx: RunContext | None = None,
    ) -> list[ToolExecutionResult]:
        """
        Execute all tool calls.

        Each tool execution receives the current RunContext
        through the runtime context variable.
        """

        if not tool_calls:
            return []

        return await asyncio.gather(
            *(
                self.execute_one(
                    tool_call,
                    ctx=ctx,
                )
                for tool_call in tool_calls
            )
        )

    def build_tool_messages(
        self,
        results: list[ToolExecutionResult],
    ) -> list[ChatMessage]:
        """
        Convert tool execution results into ToolMessages.
        """

        messages: list[ChatMessage] = []

        for result in results:
            output = result.output

            observation = getattr(
                output,
                "observation",
                None,
            )

            if observation is not None:
                content = str(
                    observation,
                )
            else:
                content = self._serialize_output(
                    output,
                )

            messages.append(
                ChatMessage.tool(
                    tool_call_id=result.tool_call.id,
                    name=result.tool_call.name,
                    content=content,
                )
            )

        return messages

    @staticmethod
    def _serialize_output(
        output: Any,
    ) -> str:
        """
        Serialize a tool result into message content.
        """

        if output is None:
            return ""

        if isinstance(
            output,
            str,
        ):
            return output

        try:
            return json.dumps(
                output,
                ensure_ascii=False,
                default=str,
            )

        except Exception:
            return str(
                output,
            )
