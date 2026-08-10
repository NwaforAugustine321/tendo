from __future__ import annotations
from app.toolsets.tool_search import ToolSearchToolset
from app.toolsets.utils import prepare_function_arguments
from app.toolsets.tool_context import (
    NOT_GIVEN,
    NotGivenOr,
    ProviderTool,
    RunContext,
    SearchStrategy,
    Tool,
    ToolContext,
    ToolError,
    Toolset,
    _build_tool_schema,
    function_tool,
)

import asyncio
import json
import sys
import os
from typing import Any

from typing_extensions import Self

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..')))


_DEFAULT_CALL_DESCRIPTION = (
    "Call a tool by name with the given arguments. "
    "Use search_tools to discover available tools and their schemas if it isn't already loaded."
)


class ToolProxyToolset(ToolSearchToolset):
    """
    Exposes exactly two fixed tools:

    - search_tools
    - call_tool

    Unlike ToolSearchToolset, the available tools never change.
    search_tools returns tool schemas and call_tool executes a tool by name.
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

        self._tool_ctx: ToolContext | None = None

        call_description = call_description or _DEFAULT_CALL_DESCRIPTION

        self._call_tool = function_tool(
            self._handle_call,
            raw_schema={
                "name": "call_tool",
                "description": call_description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the tool to call",
                        },
                        "parameters": {
                            "type": "object",
                            "description": "The parameters to pass to the tool",
                        },
                    },
                    "required": ["name", "parameters"],
                },
            },
        )

    @property
    def tools(self) -> list[Tool | Toolset]:
        """ToolProxyToolset always exposes exactly two tools."""
        return [
            self._search_tool,
            self._call_tool,
        ]

    async def setup(
        self,
        *,
        reload: bool = False,
    ) -> Self:
        """Initialize the search index and build a ToolContext used by call_tool()."""

        await super().setup(reload=reload)
        self._tool_ctx = ToolContext(self._tools)
        return self

    async def _handle_search(
        self,
        raw_arguments: dict[str, object],
    ) -> str:
        """Search for matching tools and return their schemas."""

        query = str(raw_arguments.get("query", ""))

        if not query:
            raise ToolError("query cannot be empty")

        tools = await self._search_tools(query)

        if not tools:
            return f"No tools found matching '{query}'. Try a different search query related to the tool."

        tool_ctx = ToolContext(tools)

        schemas = []
        # Build schemas for FunctionTools
        for ft in tool_ctx.function_tools.values():
            schemas.append(_build_tool_schema(ft))
        # Build schemas for ProviderTools
        for pt in tool_ctx.provider_tools:
            schema: dict[str, Any] = {
                "name": pt.name,
                "description": pt.description,
                "parameters": pt.args_schema.model_json_schema() if pt.args_schema else {"type": "object", "properties": {}},
            }
            schemas.append(schema)

        return "\n".join(json.dumps(s) for s in schemas)

    async def _handle_call(
        self,
        ctx: RunContext,
        raw_arguments: dict[str, object],
    ) -> Any:
        """Execute a tool by name."""

        name = str(raw_arguments.get("name", ""))
        parameters = raw_arguments.get("parameters")

        if not name:
            raise ToolError("tool name cannot be empty")

        if parameters is None:
            raise ToolError("parameters is required")

        if not isinstance(parameters, (dict, str)):
            raise ToolError("parameters must be a dictionary or a string")

        if self._tool_ctx is None:
            raise RuntimeError("toolset not initialized, call setup() first")

        # If the LLM tries to call tool_search through call_tool, redirect
        if name == "tool_search":
            search_params = parameters if isinstance(
                parameters, dict) else json.loads(parameters)
            return await self._handle_search(search_params)

        # Check FunctionTools first
        fnc_tool = self._tool_ctx.get_function_tool(name)
        if fnc_tool is not None:
            fnc_args, fnc_kwargs = prepare_function_arguments(
                fnc=fnc_tool,
                json_arguments=parameters,
                call_ctx=ctx,
            )
            result = fnc_tool(*fnc_args, **fnc_kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            return result

        # Check ProviderTools
        for pt in self._tool_ctx.provider_tools:
            if pt.name == name:
                args = parameters if isinstance(
                    parameters, dict) else json.loads(parameters)
                try:
                    return await pt.ainvoke(args)
                except (NotImplementedError, TypeError):
                    return pt.invoke(args)

        raise ToolError(
            f"unknown tool '{name}', "
            "use search_tools to discover available tools"
        )

    def to_langchain_tools(self) -> list:
        """Return search_tools and call_tool as LangChain StructuredTool instances."""
        from langchain_core.tools import StructuredTool
        from pydantic import create_model, Field as PydanticField

        lc_tools = []

        for raw_tool, handler in [
            (self._search_tool, self._handle_search),
            (self._call_tool, self._handle_call),
        ]:
            schema = raw_tool.info.raw_schema
            tool_name = schema["name"]
            description = schema.get("description", "")
            params = schema.get("parameters", {}).get("properties", {})
            required = schema.get("parameters", {}).get("required", [])

            fields = {}
            for p_name, p_info in params.items():
                p_type = dict if p_info.get("type") == "object" else str
                default = ... if p_name in required else None
                fields[p_name] = (p_type, PydanticField(
                    default=default, description=p_info.get("description", "")))

            args_model = create_model(f"{tool_name}_Args", **fields)

            async def _coroutine(_handler=handler, **kwargs):
                # For call_tool handler, pass None as ctx since we don't have a RunContext
                if _handler == self._handle_call:
                    return await _handler(None, kwargs)
                return await _handler(kwargs)

            lc_tools.append(StructuredTool(
                name=tool_name,
                description=description,
                args_schema=args_model,
                coroutine=_coroutine,
            ))

        return lc_tools

    def to_openai_tools(self) -> list[dict[str, Any]]:
        """Return search_tools and call_tool in OpenAI function-calling format.

        Returns a list of dicts compatible with OpenAI's `tools` parameter:
        [{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}]
        """
        tools = []
        for raw_tool in [self._search_tool, self._call_tool]:
            schema = raw_tool.info.raw_schema
            tools.append({
                "type": "function",
                "function": {
                    "name": schema["name"],
                    "description": schema.get("description", ""),
                    "parameters": schema.get("parameters", {}),
                },
            })
        return tools

    def to_anthropic_tools(self) -> list[dict[str, Any]]:
        """Return search_tools and call_tool in Anthropic tool format.

        Returns a list of dicts compatible with Anthropic's `tools` parameter:
        [{"name": ..., "description": ..., "input_schema": ...}]
        """
        tools = []
        for raw_tool in [self._search_tool, self._call_tool]:
            schema = raw_tool.info.raw_schema
            tools.append({
                "name": schema["name"],
                "description": schema.get("description", ""),
                "input_schema": schema.get("parameters", {}),
            })
        return tools


# ---------------------------------------------------------------------------
# Test / demo code
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from langchain_core.tools import tool

    @tool
    def send_email(to: str, subject: str) -> str:
        """Send an email."""
        return "Email sent"

    @tool
    def github_issue(title: str) -> str:
        """Create a GitHub issue."""
        return "Issue created"

    async def _main():
        proxy = ToolProxyToolset(
            id="proxy",
            tools=[
                ProviderTool(send_email),
                ProviderTool(github_issue),
            ],
        )

        await proxy.setup()

        # Get LangChain tools for LLM binding
        lc_tools = proxy.to_langchain_tools()
        print("LangChain tools:", [t.name for t in lc_tools])

        # Search for tools
        search_tool = lc_tools[0]  # tool_search
        result = await search_tool.ainvoke({"query": "email"})
        print("Search result:", result)

        # Call a tool
        call_tool = lc_tools[1]  # call_tool
        result = await call_tool.ainvoke({"name": "send_email", "parameters": {"to": "user@example.com", "subject": "Hello"}})
        print("Call result:", result)

    asyncio.run(_main())
