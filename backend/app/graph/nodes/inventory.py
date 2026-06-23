"""Inventory agent node — handles inventory and product operations.

Call-stack architecture: inventory owns its workflow. When it needs DB data
via tool_planner, it sets return_to to itself. When re-entered with domain_result,
it processes the returned data and continues.
"""

import json
import logging

from app.agents.models import Agent, DomainAgentOutput
from app.db.tools.inventory_tools import INVENTORY_TOOLS
from app.lib.agent_executor import execute_task
from app.lib.user_input_tool import ask_user_question
from app.memory.memory import Memory, get_memory
from app.models.state import GraphState

logger = logging.getLogger(__name__)

# Load agent once at module level — not recomputed per request
_inventory_agent = Agent.from_spec("domain/inventory")


async def inventory_node(state: GraphState) -> dict:
    event = state.get("event", {})
    user_message = event.get("text", "")
    business_id = state.get("business_id") or event.get("business_id", "")
    thread_id = state.get("thread_id") or event.get("thread_id", "")
    history = state.get("messages", [])

    from app.lib.field_formatter import format_user_input
    user_message = format_user_input(user_message)

    # Return from tool_planner (db_translator just ran)
    domain_result = state.get("domain_result")
    if domain_result and state.get("return_to") == "inventory":
        summary = domain_result.get("summary", "")
        logger.info(f"Inventory: got tool results back — {summary[:100]}")

        response_data = {"mode": "conversation", "text": summary}
        return {
            "response": response_data,
            "output_mode": "conversation",
            "domain_result": None,
            "return_to": None,
            "workflow_owner": None,
            "current_agent": None,
            "tool_requests": None,
            "messages": [
                {"role": "assistant", "content": summary},
            ],
        }

    # Use module-level agent (loaded once)
    agent = _inventory_agent

    # Context (business-specific only — tools are injected via prompts.py)
    context = f"business_id: {business_id}\nthread_id: {thread_id}"

    # Memory for this business
    memory = get_memory(f"/business/{business_id}")

    # Execute using our lib pipeline
    raw = await execute_task(
        agent=agent,
        description=user_message,
        tools=INVENTORY_TOOLS + [ask_user_question],
        expected_output=agent.expected_output,
        chat_history=history[-12:],
        context=context,
        output_pydantic=DomainAgentOutput,
        memory=memory,
        use_system_prompt=True,
        max_iter=3,
    )

    logger.info(f"Inventory raw output: {raw[:200]}")

    # Parse response
    parsed = _parse_response(raw)
    text = parsed.get("response", raw)
    fields = parsed.get("fields")
    tool_requests = parsed.get("tool_requests")

    response_data = {"mode": "conversation", "text": text}
    if fields:
        response_data["input"] = {"fields": fields}

    result = {
        "response": response_data,
        "output_mode": "conversation",
        "workflow_owner": "inventory",
        "current_agent": "inventory",
        "messages": [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": raw},
        ],
    }

    # If the specialist needs DB operations via tool_planner
    if tool_requests and isinstance(tool_requests, list):
        clean_requests = [
            {"tool": tr.get("tool", ""), "arguments": tr.get("arguments", tr.get("params", {}))}
            for tr in tool_requests
            if isinstance(tr, dict)
        ]
        result["tool_requests"] = clean_requests
        result["return_to"] = "inventory"
        result["workflow_owner"] = "inventory"

    return result


def _parse_response(raw: str) -> dict:
    """Parse agent JSON output. Also handles __WAITING__ tool signal."""
    # Handle __WAITING__ signal from ask_user_question tool
    if "__WAITING__|" in raw:
        try:
            json_part = raw.split("__WAITING__|", 1)[1]
            return json.loads(json_part)
        except (json.JSONDecodeError, IndexError):
            return {"response": raw.strip(), "workflow_status": "waiting_for_user"}

    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        start = clean.find("{")
        if start != -1:
            depth = 0
            for i in range(start, len(clean)):
                if clean[i] == "{":
                    depth += 1
                elif clean[i] == "}":
                    depth -= 1
                    if depth == 0:
                        parsed = json.loads(clean[start: i + 1])
                        if "response" in parsed:
                            return parsed
                        break
        return json.loads(clean)
    except (json.JSONDecodeError, IndexError, ValueError):
        return {"response": raw.strip(), "workflow_status": "completed"}
