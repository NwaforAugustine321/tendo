"""Tool Planner node — converts natural language intent to structured tool call requests."""

import json
import logging

from app.lib.tool_schema import registry_tools_to_prompt, tools_to_prompt
from app.llm.client import get_client as get_llm
from app.llm.specs import load
from app.memory.tools import MEMORY_TOOLS
from app.models.state import GraphState

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 2


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
    business_id = state.get("business_id") or event.get("business_id", "")
    domain_result = state.get("domain_result")

    config = load("tool_planner")
    llm = get_llm()

    # Bind memory tools so tool_planner can fetch context if needed
    llm_with_tools = llm.bind_tools(MEMORY_TOOLS)

    # Dynamically inject all registered DB tool schemas
    dynamic_tools = registry_tools_to_prompt()
    system_content = config.system_prompt
    system_content += f"\n\n## Available DB Tools (auto-generated)\n\n{dynamic_tools}"
    system_content += f"\n\n## Available Memory Tools\n{tools_to_prompt(MEMORY_TOOLS)}"
    system_content += f"\n\nNOTE: business_id is auto-injected as '{business_id}' — only include it if different."

    prompt = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": f"User request: {user_message}\nContext: {json.dumps(domain_result or {})}"},
    ]

    # Tool-calling loop — tool planner can call memory tools before planning
    for iteration in range(MAX_TOOL_ITERATIONS):
        llm_response = await llm_with_tools.ainvoke(prompt)

        if llm_response.tool_calls:
            logger.info(f"Tool planner: calling {len(llm_response.tool_calls)} tool(s): {[tc['name'] for tc in llm_response.tool_calls]}")
            prompt.append({"role": "assistant", "content": llm_response.content or "", "tool_calls": llm_response.tool_calls})

            # Execute tools in parallel
            import asyncio

            async def _run_tool(tc):
                name = tc["name"]
                args = dict(tc["args"])
                if "business_id" in args and not args["business_id"]:
                    args["business_id"] = business_id
                res = await _execute_tool(name, args)
                logger.info(f"Tool planner: tool {name} returned {len(res)} chars")
                return tc["id"], res

            tool_results = await asyncio.gather(*[_run_tool(tc) for tc in llm_response.tool_calls])

            for call_id, result in tool_results:
                prompt.append({"role": "tool", "tool_call_id": call_id, "content": result})
            continue

        raw = llm_response.content.strip()
        break
    else:
        raw = llm_response.content.strip() if llm_response.content else "[]"

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


async def _execute_tool(tool_name: str, tool_args: dict) -> str:
    """Execute a memory tool by name."""
    tool_map = {t.name: t for t in MEMORY_TOOLS}
    tool_fn = tool_map.get(tool_name)
    if not tool_fn:
        return f"Unknown tool: {tool_name}"
    try:
        result = await tool_fn.ainvoke(tool_args)
        return str(result)
    except Exception as e:
        logger.warning(f"Tool planner tool {tool_name} failed: {e}")
        return f"Tool error: {e}"
