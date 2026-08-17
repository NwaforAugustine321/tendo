from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass
from typing import Any, Literal

from typing_extensions import Self

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
        selected_tool: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)

        self.expected = expected
        self.received = received
        self.selected_tool = selected_tool
        self.instruction = instruction


@dataclass(
    slots=True,
)
class ToolResult:

    type: Literal[
        "tool_search",
        "execution",
        "validation_error",
        "tool_error",
        "no_tool_found",
        "tool_result",
        "runtime_error",
    ]

    observation: str | None = None

    def __post_init__(self) -> None:
        if isinstance(
            self.observation,
            (list, tuple),
        ):
            self.observation = "".join(
                str(item)
                for item in self.observation
            )


@dataclass(
    slots=True,
)
class ToolExecutionResult:

    tool_call: ToolCall

    result: ToolResult


_DEFAULT_CALL_DESCRIPTION = (
    "Execute a previously discovered tool and return its actual result. "
    "tool_search discovers available tools; call_tool executes a tool. "
    "The name parameter MUST be the exact name of one of the tools returned "
    "by tool_search. "
    "Never pass tool_search or call_tool as the target tool name. "
    "Provide the exact required parameters from the discovered tool schema."
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

        build_result = self._strategy.build_index(
            self._search_items,
        )

        if inspect.isawaitable(
            build_result,
        ):
            try:
                loop = asyncio.get_running_loop()

                loop.create_task(
                    self._async_build_index(),
                )

                build_result.close()

            except RuntimeError:
                asyncio.run(
                    build_result,
                )

                self._initialized = True

        else:
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
                            "description": (
                                "Exact name of a tool previously "
                                "returned by tool_search."
                            ),
                        },
                        "parameters": {
                            "type": "object",
                            "description": (
                                "Arguments required by the selected tool."
                            ),
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

    async def _async_build_index(
        self,
    ) -> None:

        await self._strategy.build_index(
            self._search_items,
        )

        self._initialized = True

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
                    ),
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
                "No runtime tool was executed.\n\n"
                f"Unknown runtime tool '{name}'.\n"
                "Use tool_search to discover available tools."
            ),
        )

    async def search(
        self,
        *,
        query: str,
    ) -> ToolResult:

        try:

            query = query.strip()

            if not query:
                return ToolResult(
                    type="validation_error",
                    observation=(
                        "TOOL DISCOVERY FAILED.\n\n"
                        "The tool search query cannot be empty."
                    ),
                )

            tools = await self._search_tools(
                query,
            )

            if not tools:
                return ToolResult(
                    type="no_tool_found",
                    observation=(
                        "TOOL DISCOVERY RESULT.\n\n"
                        f"Search intent: {query}\n\n"
                        "No available tool matched this request."
                    ),
                )

            self._selected_tools = ToolContext(
                tools,
            )

            schemas: list[dict[str, Any]] = []

            for tool in (
                self._selected_tools.function_tools.values()
            ):
                schemas.append(
                    _build_tool_schema(
                        tool,
                    ),
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
                    },
                )

            formatted_tools = self._format_discovered_tools(
                schemas,
            )

            return ToolResult(
                type="tool_search",
                observation=(
                    "TOOL DISCOVERY RESULT.\n\n"
                    "The following tools were discovered and are "
                    "available for execution:\n\n"
                    f"{formatted_tools}\n\n"
                    "IMPORTANT:\n"
                    "This result only describes the available tools.\n"
                    "Use call_tool to execute the appropriate "
                    "discovered tool."
                ),
            )

        except Exception as exc:

            return ToolResult(
                type="runtime_error",
                observation=(
                    "TOOL DISCOVERY FAILED.\n\n"
                    f"Failed to discover a tool for: {query}\n"
                    f"Error: {exc}"
                ),
            )

    @staticmethod
    def _format_discovered_tools(
        schemas: list[dict[str, Any]],
    ) -> str:

        if not schemas:
            return "No executable tools were discovered."

        lines: list[str] = []

        for index, schema in enumerate(
            schemas,
            start=1,
        ):
            name = schema.get(
                "name",
                "unknown",
            )

            description = schema.get(
                "description",
                "No description provided.",
            )

            parameters = schema.get(
                "parameters",
                {},
            )

            lines.append(
                f"{index}. {name}",
            )

            lines.append(
                f"   Purpose: {description}",
            )

            properties = parameters.get(
                "properties",
                {},
            )

            required = parameters.get(
                "required",
                [],
            )

            if properties:
                lines.append(
                    "   Parameters:",
                )

                for parameter_name, parameter_schema in (
                    properties.items()
                ):
                    parameter_type = parameter_schema.get(
                        "type",
                        "any",
                    )

                    requirement = (
                        "required"
                        if parameter_name in required
                        else "optional"
                    )

                    parameter_description = parameter_schema.get(
                        "description",
                        "",
                    )

                    description_suffix = (
                        f" — {parameter_description}"
                        if parameter_description
                        else ""
                    )

                    lines.append(
                        f"   - {parameter_name}: "
                        f"{parameter_type} "
                        f"({requirement})"
                        f"{description_suffix}",
                    )

            else:
                lines.append(
                    "   Parameters: none",
                )

            lines.append("")

        return "\n".join(
            lines,
        ).rstrip()

    def _parse_call_arguments(
        self,
        raw_arguments: dict[str, Any],
    ) -> tuple[
        str,
        dict[str, Any] | str,
    ] | ToolResult:

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
                    "TOOL EXECUTION FAILED.\n\n"
                    "Invalid call_tool parameters.\n\n"
                    "Expected:\n"
                    "{\n"
                    '  "name": "<discovered_tool_name>",\n'
                    '  "parameters": {}\n'
                    "}\n\n"
                    "Received:\n"
                    f"{raw_arguments}"
                ),
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
                    "TOOL EXECUTION FAILED.\n\n"
                    "The 'parameters' field must be an object "
                    "or JSON string.\n\n"
                    f"Received: {raw_arguments}"
                ),
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
                    "TOOL EXECUTION FAILED.\n\n"
                    "No tool has been discovered yet.\n\n"
                    "Use tool_search first, then call_tool "
                    "with the discovered tool name."
                ),
            )

        parsed = self._parse_call_arguments(
            raw_arguments,
        )

        if isinstance(
            parsed,
            ToolResult,
        ):
            return parsed

        name, parameters = parsed

        if name in {
            "tool_search",
            "call_tool",
        }:
            return ToolResult(
                type="validation_error",
                observation=(
                    "TOOL EXECUTION FAILED.\n\n"
                    f"'{name}' is a runtime proxy tool and cannot "
                    "be executed through call_tool.\n\n"
                    "call_tool must receive the exact name of a "
                    "tool discovered by tool_search."
                ),
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
                    "TOOL EXECUTION RESULT.\n\n"
                    f"Executed tool: {name}\n\n"
                    "Actual result:\n"
                    f"{result}"
                ),
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
                        "TOOL EXECUTION RESULT.\n\n"
                        f"Executed tool: {name}\n\n"
                        "Actual result:\n"
                        f"{result}"
                    ),
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
                        "TOOL EXECUTION RESULT.\n\n"
                        f"Executed tool: {name}\n\n"
                        "Actual result:\n"
                        f"{result}"
                    ),
                )

        available = list(
            self._selected_tools.function_tools.keys(),
        )

        available.extend(
            tool.name
            for tool in self._selected_tools.provider_tools
        )

        return ToolResult(
            type="tool_error",
            observation=(
                "TOOL EXECUTION FAILED.\n\n"
                f"Tool '{name}' was not one of the discovered tools.\n\n"
                "Available discovered tools:\n"
                f"{', '.join(available)}\n\n"
                "Use the exact discovered tool name."
            ),
        )
