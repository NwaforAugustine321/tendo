"""DB Oracle node — executes tool requests against the database in parallel."""

import asyncio
import logging

from app.db.node import execute_tool
from app.models.state import GraphState

logger = logging.getLogger(__name__)


async def db_node(state: GraphState) -> dict:
    """Execute all pending tool requests in parallel."""
    tool_requests = state.get("tool_requests") or []

    if not tool_requests:
        logger.info("DB node: no tool requests")
        return {"db_result": {}, "tool_requests": None}

    business_id = state.get("business_id") or "default"

    async def _exec(request: dict) -> dict:
        tool_name = request.get("tool")
        params = request.get("params", {})
        if "business_id" not in params:
            params["business_id"] = business_id
        logger.info(f"DB node: executing {tool_name}")
        try:
            result = await execute_tool(tool_name, params)
            return {"tool": tool_name, "success": True, "data": result}
        except Exception as e:
            logger.error(f"DB node: {tool_name} failed: {e}")
            return {"tool": tool_name, "success": False, "error": str(e)}

    results = await asyncio.gather(*[_exec(r) for r in tool_requests])

    return {"db_result": {"results": list(results)}, "tool_requests": None}
