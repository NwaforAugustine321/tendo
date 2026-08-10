from __future__ import annotations

import asyncio
import inspect
from collections.abc import Sequence
from typing import Any

from typing_extensions import Self

from app.toolsets.tool_context import (
    BM25SearchStrategy,
    FunctionTool,
    NOT_GIVEN,
    NotGivenOr,
    ProviderTool,
    RawFunctionTool,
    SearchItem,
    SearchStrategy,
    Tool,
    ToolContext,
    ToolError,
    Toolset,
    _build_tool_schema,
    _get_tool_description,
    _get_tool_params,
    function_tool,
)


_DEFAULT_SEARCH_DESCRIPTION = (
    "Search for available tools by describing what you need. "
    "Returns the schemas of matching tools. Use call_tool to invoke them."
)

_DEFAULT_QUERY_DESCRIPTION = (
    "keywords to search for in the tool names and descriptions, split by spaces"
)


class ToolSearchToolset(Toolset):

    def __init__(
        self,
        *,
        id: str,
        tools: list[Tool | Toolset] | None = None,
        max_results: int = 5,
        search_strategy: NotGivenOr[SearchStrategy] = NOT_GIVEN,
        search_description: NotGivenOr[str] = NOT_GIVEN,
        query_description: NotGivenOr[str] = NOT_GIVEN,
    ) -> None:

        super().__init__(id=id, tools=tools)

        self._strategy = search_strategy or BM25SearchStrategy()
        self._max_results = max_results

        self._loaded_tools: list[Tool | Toolset] = []
        self._search_items: list[SearchItem] = []

        self._initialized = False
        self._lock = asyncio.Lock()

        search_description = search_description or _DEFAULT_SEARCH_DESCRIPTION
        query_description = query_description or _DEFAULT_QUERY_DESCRIPTION

        self._search_tool = function_tool(
            self._handle_search,
            raw_schema={
                "name": "tool_search",
                "description": search_description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": query_description,
                        }
                    },
                    "required": ["query"],
                },
            },
        )

    @property
    def tools(self) -> list[Tool | Toolset]:
        return [
            self._search_tool,
            *self._loaded_tools,
        ]

    async def setup(
        self,
        *,
        reload: bool = False,
    ) -> Self:

        await super().setup()

        async with self._lock:

            if not reload and self._initialized:
                return self

            toolsets = [
                tool
                for tool in self._tools
                if isinstance(tool, Toolset)
            ]

            if toolsets:
                await asyncio.gather(
                    *(toolset.setup() for toolset in toolsets)
                )

            self._search_items.clear()

            for tool in self._tools:
                self._index_tool(tool=tool, source=tool)

            result = self._strategy.build_index(self._search_items)

            if inspect.isawaitable(result):
                await result

            self._initialized = True

            return self

    def _index_tool(
        self,
        tool: Tool | Toolset,
        source: Tool | Toolset,
    ) -> None:
        """Recursively index tools. Every executable tool becomes a SearchItem."""

        # Nested Toolset
        if isinstance(tool, Toolset):
            tool_ctx = ToolContext([tool])
            for nested_tool in tool_ctx.flatten():
                self._index_tool(tool=nested_tool, source=source)
            return

        # FunctionTool
        if isinstance(tool, FunctionTool):
            self._search_items.append(
                SearchItem(
                    source=source,
                    name=tool.id,
                    description=_get_tool_description(tool),
                    parameters=_get_tool_params(tool),
                )
            )
            return

        # RawFunctionTool
        if isinstance(tool, RawFunctionTool):
            self._search_items.append(
                SearchItem(
                    source=source,
                    name=tool.id,
                    description=_get_tool_description(tool),
                    parameters=_get_tool_params(tool),
                )
            )
            return

        # ProviderTool
        if isinstance(tool, ProviderTool):
            # Extract params from args_schema if available
            params = {}
            if tool.args_schema:
                for field_name, field_info in tool.args_schema.model_fields.items():
                    params[field_name] = field_info.description or ""

            self._search_items.append(
                SearchItem(
                    source=source,
                    name=tool.id,
                    description=tool.description,
                    parameters=params,
                )
            )
            return

        raise ValueError(f"Unsupported tool type: {type(tool)}")

    async def _search_tools(
        self,
        query: str,
    ) -> list[Tool | Toolset]:
        """Search for matching tools."""

        if not query:
            raise ToolError("query cannot be empty")

        results = self._strategy.search(
            query=query,
            items=self._search_items,
            max_results=self._max_results,
        )

        if inspect.isawaitable(results):
            results = await results

        return list(dict.fromkeys(item.source for item in results))

    async def _handle_search(
        self,
        raw_arguments: dict[str, object],
    ) -> str:
        """Handle the tool_search function call."""

        query = str(raw_arguments.get("query", ""))

        tools = await self._search_tools(query)

        if not tools:
            raise ToolError(f"No tools found matching '{query}'.")

        self._loaded_tools = tools

        return "Tools loaded successfully."

    async def aclose(self) -> None:
        await super().aclose()

        self._initialized = False
        self._search_items.clear()
        self._loaded_tools.clear()

        result = self._strategy.cleanup()
        if inspect.isawaitable(result):
            await result
