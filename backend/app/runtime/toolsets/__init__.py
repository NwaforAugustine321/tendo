"""Toolsets package — tool search, proxy, and utilities."""

from app.toolsets.tool_context import (
    BM25SearchStrategy,
    DuplicateMode,
    DuplicateScope,
    FunctionTool,
    FunctionToolInfo,
    KeywordSearchStrategy,
    NOT_GIVEN,
    NotGiven,
    NotGivenOr,
    ProviderTool,
    RawFunctionDescription,
    RawFunctionTool,
    RawFunctionToolInfo,
    RunContext,
    SearchItem,
    SearchStrategy,
    Tool,
    ToolContext,
    ToolError,
    ToolFlag,
    Toolset,
    _build_tool_schema,
    _get_tool_description,
    _get_tool_params,
    find_function_tools,
    function_arguments_to_pydantic_model,
    function_tool,
    get_fnc_tool_names,
    get_function_info,
    get_raw_function_info,
    is_context_type,
    is_function_tool,
    is_raw_function_tool,
    parse_function_arguments,
    prepare_function_arguments,
)
from app.toolsets.tool_search import ToolSearchToolset
from app.toolsets.tool_proxy import ToolProxyToolset

__all__ = [
    # Core types
    "NotGiven",
    "NotGivenOr",
    "NOT_GIVEN",
    "ToolFlag",
    "Tool",
    "ProviderTool",
    "DuplicateMode",
    "DuplicateScope",
    "FunctionToolInfo",
    "RawFunctionDescription",
    "RawFunctionToolInfo",
    "FunctionTool",
    "RawFunctionTool",
    "RunContext",
    "ToolError",
    # Decorator
    "function_tool",
    # Helpers
    "is_function_tool",
    "get_function_info",
    "is_raw_function_tool",
    "get_raw_function_info",
    "find_function_tools",
    "get_fnc_tool_names",
    # Argument utilities
    "function_arguments_to_pydantic_model",
    "is_context_type",
    "parse_function_arguments",
    "prepare_function_arguments",
    # Toolset
    "Toolset",
    # Search
    "SearchItem",
    "SearchStrategy",
    "KeywordSearchStrategy",
    "BM25SearchStrategy",
    # Schema helpers
    "_get_tool_description",
    "_get_tool_params",
    "_build_tool_schema",
    # Context & toolsets
    "ToolContext",
    "ToolSearchToolset",
    "ToolProxyToolset",
]
