from __future__ import annotations

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


@dataclass(slots=True)
class ToolExecutionResult:
    """
    Result of executing a single tool.
    """

    tool_call: ToolCall
    output: Any


class ToolExecutor:
    """
    Executes runtime tools.

    Responsibilities
    ----------------
    - Delegate execution to ToolProxyToolset
    - Convert execution failures into ToolMessages
    """

    def __init__(
        self,
        proxy: ToolProxyToolset,
    ) -> None:

        self._proxy = proxy

    async def execute_one(
        self,
        tool_call: ToolCall,
        *,
        ctx: RunContext | None = None,
    ) -> ToolExecutionResult:

        try:

            output = await self._proxy.execute(
                name=tool_call.name,
                arguments=tool_call.arguments,
                ctx=ctx,
            )

        except ToolProtocolError as error:

            output = {
                "type": "tool_protocol_error",
                "error": str(error),
                "expected": error.expected,
                "received": error.received,
            }

        except ToolError as error:

            output = {
                "type": "tool_error",
                "error": str(error),
            }

        except Exception as error:

            output = {
                "type": "tool_runtime_error",
                "error": type(error).__name__,
                "message": str(error),
            }

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

        return [
            await self.execute_one(
                tool_call,
                ctx=ctx,
            )
            for tool_call in tool_calls
        ]

    def build_tool_messages(
        self,
        results: list[ToolExecutionResult],
    ) -> list[ChatMessage]:

        messages: list[ChatMessage] = []

        for result in results:

            output = result.output

            if output is None:

                content = ""

            elif isinstance(
                output,
                str,
            ):

                content = output

            else:

                try:

                    content = json.dumps(
                        output,
                        ensure_ascii=False,
                        default=str,
                    )

                except Exception:

                    content = str(output)

            messages.append(
                ChatMessage.tool(
                    tool_call_id=result.tool_call.id,
                    name=result.tool_call.name,
                    content=content,
                )
            )

        return messages
