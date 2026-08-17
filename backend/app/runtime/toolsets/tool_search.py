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
    _get_tool_description,
    _get_tool_params,
    function_tool,
)

from .strategies.hybrid_search_strategy import HybridSearchStrategy
from .strategies.bm25_search_strategy import BM25SearchStrategy
from .strategies.semantic_search_strategy import SemanticSearchStrategy


_DEFAULT_SEARCH_DESCRIPTION = (
    "Discover available tools or capabilities that can provide information "
    "or perform an action required by the user's request. "
    "Use this tool when the required information or capability is not "
    "available in the current conversation or may exist in another "
    "available tool. "

    "Search using the intent of the request and the information or action "
    "required, not only exact words from the user's message. Rephrase the "
    "request into concise search terms describing what capability or "
    "information is needed. "

    "When the request depends on information that may have been previously "
    "learned, discussed, stored, decided, observed, or accumulated, search "
    "for the appropriate retrieval capability. This can include memory, "
    "knowledge, documents, records, entities, relationships, decisions, "
    "history, or other stored information. "

    "If the request can be completed using the current conversation and "
    "available context, tool discovery is not required. "

    "This tool only discovers available tools. After discovering the "
    "appropriate tool, use call_tool with the exact discovered tool name "
    "and its required parameters to execute it."
)


_DEFAULT_QUERY_DESCRIPTION = (
    "Concise search terms describing the capability or information needed "
    "to complete the user's request. Use intent and relevant facts rather "
    "than copying the entire user message. "

    "When the request depends on previously known, discussed, stored, or "
    "accumulated information, describe the retrieval need so that relevant "
    "memory, knowledge, documents, records, or other retrieval capabilities "
    "can be discovered."
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

        super().__init__(
            id=id,
            tools=tools,
        )

        self._strategy = (
            search_strategy
            if (
                search_strategy is not None
                and not isinstance(
                    search_strategy,
                    NotGiven,
                )
            )
            else HybridSearchStrategy(
                bm25=BM25SearchStrategy(),
                vector=SemanticSearchStrategy(),
            )
        )

        self._max_results = max_results

        self._loaded_tools: list[
            Tool | Toolset
        ] = []

        self._search_items: list[
            SearchItem
        ] = []

        self._initialized = False

        self._lock = asyncio.Lock()

        search_description = (
            search_description
            or _DEFAULT_SEARCH_DESCRIPTION
        )

        query_description = (
            query_description
            or _DEFAULT_QUERY_DESCRIPTION
        )

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
                        },
                    },
                    "required": [
                        "query",
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
            *self._loaded_tools,
        ]

    async def setup(
        self,
        *,
        reload: bool = False,
    ) -> Self:

        await super().setup()

        async with self._lock:

            if (
                not reload
                and self._initialized
            ):
                return self

            toolsets = [
                tool
                for tool in self._tools
                if isinstance(
                    tool,
                    Toolset,
                )
            ]

            if toolsets:
                await asyncio.gather(
                    *(
                        toolset.setup()
                        for toolset in toolsets
                    )
                )

            self._search_items.clear()

            for tool in self._tools:
                self._index_tool(
                    tool=tool,
                    source=tool,
                )

            result = self._strategy.build_index(
                self._search_items,
            )

            if inspect.isawaitable(
                result,
            ):
                await result

            self._initialized = True

            return self

    def _index_tool(
        self,
        tool: Tool | Toolset,
        source: Tool | Toolset,
    ) -> None:
        """
        Recursively index executable tools.
        """

        if isinstance(
            tool,
            Toolset,
        ):
            tool_ctx = ToolContext(
                [tool],
            )

            for nested_tool in tool_ctx.flatten():
                self._index_tool(
                    tool=nested_tool,
                    source=source,
                )

            return

        if isinstance(
            tool,
            FunctionTool,
        ):
            self._search_items.append(
                SearchItem(
                    source=source,
                    name=tool.id,
                    description=_get_tool_description(
                        tool,
                    ),
                    parameters=_get_tool_params(
                        tool,
                    ),
                )
            )

            return

        if isinstance(
            tool,
            RawFunctionTool,
        ):
            self._search_items.append(
                SearchItem(
                    source=source,
                    name=tool.id,
                    description=_get_tool_description(
                        tool,
                    ),
                    parameters=_get_tool_params(
                        tool,
                    ),
                )
            )

            return

        if isinstance(
            tool,
            ProviderTool,
        ):
            params: dict[str, str] = {}

            if tool.args_schema:
                for (
                    field_name,
                    field_info,
                ) in tool.args_schema.model_fields.items():

                    params[field_name] = (
                        field_info.description
                        or ""
                    )

            self._search_items.append(
                SearchItem(
                    source=source,
                    name=tool.id,
                    description=tool.description,
                    parameters=params,
                )
            )

            return

        provider_tool = ProviderTool(
            tool,
        )

        params: dict[str, str] = {}

        if provider_tool.args_schema:
            for (
                field_name,
                field_info,
            ) in provider_tool.args_schema.model_fields.items():

                params[field_name] = (
                    field_info.description
                    or ""
                )

        self._search_items.append(
            SearchItem(
                source=source,
                name=provider_tool.id,
                description=provider_tool.description,
                parameters=params,
            )
        )

    async def _search_tools(
        self,
        query: str,
    ) -> list[Tool | Toolset]:
        """
        Search for tools matching the requested capability.
        """

        query = query.strip()

        if not query:
            raise ToolError(
                "query cannot be empty",
            )

        results = self._strategy.search(
            query=query,
            items=self._search_items,
            max_results=self._max_results,
        )

        if inspect.isawaitable(
            results,
        ):
            results = await results

        seen: set[int] = set()

        unique_sources: list[
            Tool | Toolset
        ] = []

        for item in results:
            obj_id = id(
                item.source,
            )

            if obj_id in seen:
                continue

            seen.add(
                obj_id,
            )

            unique_sources.append(
                item.source,
            )

        return unique_sources

    async def _handle_search(
        self,
        raw_arguments: dict[str, object],
    ) -> str:
        """
        Discover matching tools and expose them to the proxy.
        """

        query = str(
            raw_arguments.get(
                "query",
                "",
            )
        ).strip()

        tools = await self._search_tools(
            query,
        )

        if not tools:
            raise ToolError(
                f"No tools found matching '{query}'.",
            )

        self._loaded_tools = tools

        schemas: list[
            dict[str, Any]
        ] = []

        selected_context = ToolContext(
            tools,
        )

        for tool in (
            selected_context.function_tools.values()
        ):
            schemas.append(
                {
                    "name": tool.id,
                    "description": _get_tool_description(
                        tool,
                    ),
                    "parameters": _get_tool_params(
                        tool,
                    ),
                }
            )

        for tool in selected_context.provider_tools:
            schemas.append(
                {
                    "name": tool.id,
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

        return self._format_search_result(
            schemas,
        )

    @staticmethod
    def _format_search_result(
        schemas: Sequence[
            dict[str, Any]
        ],
    ) -> str:

        if not schemas:
            return (
                "No executable tools were discovered."
            )

        lines: list[str] = [
            "TOOL DISCOVERY RESULT",
            "",
            "The following tools are available "
            "for execution:",
            "",
        ]

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

                for (
                    parameter_name,
                    parameter_schema,
                ) in properties.items():

                    parameter_type = (
                        parameter_schema.get(
                            "type",
                            "any",
                        )
                    )

                    requirement = (
                        "required"
                        if parameter_name in required
                        else "optional"
                    )

                    parameter_description = (
                        parameter_schema.get(
                            "description",
                            "",
                        )
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

        lines.extend(
            [
                "Use call_tool with the exact "
                "discovered tool name and "
                "parameters to execute a tool.",
            ]
        )

        return "\n".join(
            lines,
        )

    async def aclose(
        self,
    ) -> None:

        await super().aclose()

        self._initialized = False

        self._search_items.clear()

        self._loaded_tools.clear()

        result = self._strategy.cleanup()

        if inspect.isawaitable(
            result,
        ):
            await result
