"""Tool Planner node — converts natural language intent to structured tool call requests."""

import json
import logging

from app.llm.client import get_client as get_llm
from app.llm.specs import load
from app.models.state import GraphState

logger = logging.getLogger(__name__)


async def tool_planner_node(state: GraphState) -> dict:
    """Convert the MOA's intent into structured tool_requests using the LLM."""
    tool_requests = state.get("tool_requests")

    # If MOA already set structured tool_requests, pass through
    if tool_requests and isinstance(tool_requests, list) and len(tool_requests) > 0:
        if isinstance(tool_requests[0], dict) and "tool" in tool_requests[0]:
            logger.info(f"Tool planner: passing through {len(tool_requests)} pre-structured requests")
            return {"tool_requests": tool_requests}

    # Use LLM with the tool_planner spec to plan tools
    event = state.get("event", {})
    user_message = event.get("text", "")
    domain_result = state.get("domain_result")

    config = load("tool_planner")
    llm = get_llm()

    prompt = [
        {"role": "system", "content": config.system_prompt},
        {"role": "user", "content": f"User request: {user_message}\nContext: {json.dumps(domain_result or {})}"},
    ]

    llm_response = await llm.ainvoke(prompt)
    raw = llm_response.content.strip()

    logger.info(f"Tool planner raw: {raw[:200]}")

    # Parse the tool calls
    try:
        clean = raw
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        planned_tools = json.loads(clean)
        if not isinstance(planned_tools, list):
            planned_tools = []
    except (json.JSONDecodeError, IndexError):
        logger.warning(f"Tool planner: failed to parse response: {raw[:100]}")
        planned_tools = []

    logger.info(f"Tool planner: planned {len(planned_tools)} tool calls")
    return {"tool_requests": planned_tools if planned_tools else None}
