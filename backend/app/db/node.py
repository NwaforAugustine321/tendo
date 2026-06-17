"""DB Oracle node — executes registered tool requests."""

from app.db.registry import get_tool


def execute_tool(tool_name: str, params: dict) -> dict:
    """Execute a registered DB tool by name."""
    tool_fn = get_tool(tool_name)
    if tool_fn is None:
        return {"error": f"Unknown tool: {tool_name}"}
    return tool_fn(**params)
