from __future__ import annotations

import asyncio
import inspect
from collections.abc import Sequence
from typing import Any

from typing_extensions import Self

from .tool_context import (
    FunctionTool,
    NOT_GIVEN,
    NotGiven,
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

from .strategies.hybrid_search_strategy import HybridSearchStrategy
from .strategies.bm25_search_strategy import BM25SearchStrategy
from .strategies.semantic_search_strategy import SemanticSearchStrategy


_DEFAULT_SEARCH_DESCRIPTION = (
    "Search for tools using concise keywords and relevant facts extracted "
    "from the task's request. Do not use the entire message; rephrase it "
    "into the most relevant search terms for accurate tool retrieval. "
    "Return the schemas of the matching tools. After finding the required "
    "tools, use call_tool to execute them and obtain the results."
)

_DEFAULT_QUERY_DESCRIPTION = (
    "Search query: space-separated keywords extracted from the task's request that best match tool names and descriptions."
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

        self._strategy = (
            search_strategy
            if search_strategy is not None and not isinstance(search_strategy, NotGiven)
            else HybridSearchStrategy(
                bm25=BM25SearchStrategy(),
                vector=SemanticSearchStrategy(),
            )
        )
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

        provider_tool = ProviderTool(tool)
        params = {}
        if provider_tool.args_schema:
            for field_name, field_info in provider_tool.args_schema.model_fields.items():
                params[field_name] = field_info.description or ""

        self._search_items.append(
            SearchItem(
                source=source,
                name=provider_tool.id,
                description=provider_tool.description,
                parameters=params,
            )
        )
        return

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

        # Deduplicate by id(source) since some tools aren't hashable.
        seen = set()
        unique_sources = []
        for item in results:
            obj_id = id(item.source)
            if obj_id not in seen:
                seen.add(obj_id)
                unique_sources.append(item.source)

        return unique_sources

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
