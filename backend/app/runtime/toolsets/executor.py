from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from app.runtime.chat.message import ChatMessage
from app.runtime.llm.response import ToolCall
from app.runtime.toolsets.tool_context import (
    RunContext,
    ToolError,
)
from app.runtime.toolsets.tool_proxy import (
    ToolProtocolError,
    ToolProxyToolset,
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
    Executes runtime tools.
    """

    def __init__(
        self,
        proxy: ToolProxyToolset,
    ) -> None:

        self._proxy = proxy

    @property
    def proxy(
        self,
    ) -> ToolProxyToolset:

        return self._proxy

    async def execute_one(
        self,
        tool_call: ToolCall,
        *,
        ctx: RunContext | None = None,
    ) -> ToolExecutionResult:

        output = await self._proxy.execute(
            name=tool_call.name,
            arguments=tool_call.arguments,
            ctx=ctx,
        )

        return ToolExecutionResult(
            tool_call=tool_call,
            output=output,
        )

    async def execute(
        self,
        tool_calls: list[ToolCall],
        *,
        ctx: RunContext | None = None,
    ) -> list[ToolExecutionResult]:
        """
        Execute all tool calls.
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
        Convert tool execution results into
        ToolMessages for the conversation.
        """
        _results = []
        for result in results:
            _results.append(
                ChatMessage.tool(
                    tool_call_id=result.tool_call.id,
                    name=result.tool_call.name,
                    content=self._serialize_output(
                        result.output,
                    ),
                )
            )

            if result.output.observation:
                _results.append(
                    ChatMessage.system(
                        content=result.output.observation
                    )
                )

        return _results

    def _serialize_output(
        self,
        output: Any,
    ) -> str:

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
