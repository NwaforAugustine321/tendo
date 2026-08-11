from __future__ import annotations

import asyncio
import json
from typing import Any, Literal

from typing_extensions import Self
from dataclasses import dataclass
from .tool_search import ToolSearchToolset
from .utils import prepare_function_arguments
from .tool_context import (
    NOT_GIVEN,
    NotGivenOr,
    RunContext,
    SearchStrategy,
    Tool,
    ToolContext,
    ToolError,
    Toolset,
    _build_tool_schema,
    function_tool,
)


class ToolProtocolError(ToolError):

    def __init__(
        self,
        message: str,
        *,
        instruction: str,
        expected: dict[str, Any],
        received: dict[str, Any],
        selected_tool: dict[str, Any] | None = None
    ) -> None:

        super().__init__(message)

        self.expected = expected
        self.received = received
        self.selected_tool = selected_tool
        self.instruction = instruction


@dataclass(slots=True)
class ToolResult:

    type: Literal[
        "tool_search",
        "execution",
        "validation_error",
        "tool_error",
        "no_tool_found",
        "tool_result",
        "runtime_error"
    ]
    observation: str | None = None

    def __post_init__(self):
        if isinstance(self.observation, (list, tuple)):
            self.observation = "".join(str(s) for s in self.observation)


@dataclass(slots=True)
class ToolExecutionResult:

    tool_call: ToolCall
    result: ToolResult


_DEFAULT_CALL_DESCRIPTION = (
    "Execute a tool that was previously discovered using after tool search providing the right tool name and all optional and required parameter\n"
)


class ToolProxyToolset(ToolSearchToolset):
    """
    Runtime tool dispatcher.

    Exposes exactly two runtime tools:

    - tool_search
    - call_tool
    """

    def __init__(
        self,
        *,
        id: str,
        tools: list[Tool | Toolset] | None = None,
        max_results: int = 5,
        search_strategy: NotGivenOr[SearchStrategy] = NOT_GIVEN,
        search_description: NotGivenOr[str] = NOT_GIVEN,
        query_description: NotGivenOr[str] = NOT_GIVEN,
        call_description: NotGivenOr[str] = NOT_GIVEN,
    ) -> None:

        super().__init__(
            id=id,
            tools=tools,
            max_results=max_results,
            search_strategy=search_strategy,
            search_description=search_description,
            query_description=query_description,
        )

        self._registry = ToolContext(
            tools or [],
        )

        self._selected_tools: ToolContext | None = None

        for tool in tools or []:

            self._index_tool(
                tool=tool,
                source=tool,
            )

        self._strategy.build_index(
            self._search_items,
        )

        self._initialized = True

        call_description = (
            call_description
            or _DEFAULT_CALL_DESCRIPTION
        )

        self._call_tool = function_tool(
            self.call,
            raw_schema={
                "name": "call_tool",
                "description": call_description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Discovered tool name.",
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Arguments for the selected tool.",
                        },
                    },
                    "required": [
                        "name",
                        "parameters",
                    ],
                },
            },
        )

    @property
    def tools(
        self,
    ) -> list[Tool | Toolset]:

        return [
            self._search_tool,
            self._call_tool,
        ]

    async def setup(
        self,
        *,
        reload: bool = False,
    ) -> Self:

        await super().setup(
            reload=reload,
        )

        return self

    async def execute(
        self,
        *,
        name: str,
        arguments: dict[str, Any],
        ctx: RunContext,
    ) -> Any:

        if name == "tool_search":

            return await self.search(
                query=str(
                    arguments.get(
                        "query",
                        "",
                    )
                ),
            )

        if name == "call_tool":

            return await self.call(
                ctx=ctx,
                raw_arguments=arguments,
            )

        return ToolResult(
            type="no_tool_found",
            observation=(
                "Tool discovery completed.\n",
                f"Unknown runtime tool '{name}'."

            )
        )

    async def search(
        self,
        *,
        query: str,
    ) -> dict[str, Any]:

        try:

            if not query:
                return ToolResult(
                    type="validation_error",
                    observation=(
                        "Tool discovery completed.\n",
                        f"query cannot be empty'."

                    )
                )

            tools = await self._search_tools(
                query,
            )

            if not tools:

                return ToolResult(
                    type="no_tool_found",
                    observation=(
                        "Tool discovery completed.\n",
                        f"No tool found matching {query}\n",
                        f"Tools: []\n",
                    )
                )

            self._selected_tools = ToolContext(
                tools,
            )

            schemas: list[dict[str, Any]] = []

            for tool in self._selected_tools.function_tools.values():

                schemas.append(
                    _build_tool_schema(
                        tool,
                    )
                )

            for tool in self._selected_tools.provider_tools:

                schemas.append(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": (
                            tool.args_schema.model_json_schema()
                            if tool.args_schema
                            else {
                                "type": "object",
                                "properties": {},
                            }
                        ),
                    }
                )

            return ToolResult(
                type="tool_search",
                observation=(
                    "Tool discovery completed.\n",
                    "Selected tools:\n",
                    f"{schemas}/n",
                )
            )
        except Exception as e:
            return ToolResult(
                type="runtime_error",
                observation=(
                    "Tool discovery completed.\n",
                    f"Failed to find tool for {query}\n",
                    f"Tools: []\n",
                )
            )

    def _parse_call_arguments(
        self,
        raw_arguments: dict[str, Any],
    ) -> tuple[str, dict[str, Any] | str]:

        name = raw_arguments.get(
            "name",
        )

        parameters = raw_arguments.get(
            "parameters",
        )

        if name is None or parameters is None:
            return ToolResult(
                type="validation_error",
                observation=(
                    "Tool  completed.\n",
                    "Invalid tool params\n",
                    "Expected:\n",
                    """{
                        "name": "<tool_name>",
                        "parameters": \{}\
                    }\n""",
                    f"Received:\n",
                    f"{raw_arguments}/n",
                )
            )

        if not isinstance(
            parameters,
            (
                dict,
                str,
            ),
        ):
            return ToolResult(
                type="validation_error",
                observation=(
                    "Tool completed.\n",
                    "Invalid tool params\n",
                    "Expected:\n",
                    """{
                        "name": "<tool_name>",
                        "parameters": {}
                    }\n""",
                    f"Received:\n",
                    f"{raw_arguments}/n",
                )
            )

        return (
            str(name),
            parameters,
        )

    async def call(
        self,
        *,
        ctx: RunContext,
        raw_arguments: dict[str, Any],
    ) -> Any:

        if self._selected_tools is None:

            return ToolResult(
                type="no_tool_found",
                observation=(
                    "Tool completed.\n",
                    "No tool has been selected.\n",
                    "Use tool_search first to find tools.\n"
                )
            )

        name, parameters = self._parse_call_arguments(
            raw_arguments,
        )

        tool = self._selected_tools.get_function_tool(
            name,
        )

        if tool is not None:

            args, kwargs = prepare_function_arguments(
                fnc=tool,
                json_arguments=parameters,
                call_ctx=ctx,
            )

            result = tool(
                *args,
                **kwargs,
            )

            if asyncio.iscoroutine(
                result,
            ):
                result = await result

            return ToolResult(
                type="tool_result",
                observation=(
                    "Tool completed.\n",
                    f"Tool result:",
                    f"{result}"

                )
            )

        for tool in self._selected_tools.provider_tools:

            if tool.name != name:
                continue

            arguments = (
                parameters
                if isinstance(
                    parameters,
                    dict,
                )
                else json.loads(
                    parameters,
                )
            )

            try:

                result = await tool.ainvoke(
                    arguments,
                )
                return ToolResult(
                    type="tool_result",
                    observation=(
                        "Tool  completed.\n",
                        f"Tool result:",
                        f"{result}"

                    )
                )

            except (
                NotImplementedError,
                TypeError,
            ):

                result = tool.invoke(
                    arguments,
                )
                return ToolResult(
                    type="tool_result",
                    observation=(
                        "Tool completed.\n",
                        f"Tool result:",
                        f"{result}"

                    )
                )

        available = list(
            self._selected_tools.function_tools.keys()
        )

        available.extend(
            tool.name
            for tool in self._selected_tools.provider_tools
        )

        return ToolResult(
            type="tool_error",
            observation=(
                "Tool completed.\n",
                "Tool error\n",
                "Expected:\n",
                """{
                    "name": "<tool_name>",
                    "parameters": {}
                }\n""",
                f"Received:\n",
                f"{raw_arguments}/n",
            )
        )
