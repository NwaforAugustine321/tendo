"""DB Oracle node — executes registered tool requests."""

import inspect

from app.db.registry import get_tool


async def execute_tool(tool_name: str, params: dict) -> dict:
    """Execute a registered DB tool by name. Supports both sync and async tools."""
    tool_fn = get_tool(tool_name)
    if tool_fn is None:
        return {"error": f"Unknown tool: {tool_name}"}

    # Support both sync and async tool functions
    if inspect.iscoroutinefunction(tool_fn):
        return await tool_fn(**params)
    else:
        return tool_fn(**params)
