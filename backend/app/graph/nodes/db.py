"""DB Oracle node — executes tool requests against the database."""

import logging

from app.db.node import execute_tool
from app.models.state import GraphState

logger = logging.getLogger(__name__)


async def db_node(state: GraphState) -> dict:
    """Execute all pending tool requests from the tool_planner."""
    tool_requests = state.get("tool_requests") or []

    if not tool_requests:
        logger.info("DB node: no tool requests")
        return {"db_result": {}, "tool_requests": None}

    results = []
    for request in tool_requests:
        tool_name = request.get("tool")
        params = request.get("params", {})
        business_id = state.get("business_id") or "default"

        # Inject business_id into params if not already there
        if "business_id" not in params:
            params["business_id"] = business_id

        logger.info(f"DB node: executing {tool_name} with {params}")

        try:
            result = await execute_tool(tool_name, params)
            results.append({"tool": tool_name, "success": True, "data": result})
        except Exception as e:
            logger.error(f"DB node: {tool_name} failed: {e}")
            results.append({"tool": tool_name, "success": False, "error": str(e)})

    return {"db_result": {"results": results}, "tool_requests": None}
