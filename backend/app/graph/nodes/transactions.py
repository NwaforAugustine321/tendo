"""Transactions agent node — handles transaction-related operations.

Call-stack architecture: transactions owns its workflow. When it needs DB data
via tool_planner, it sets return_to to itself. When re-entered with domain_result,
it processes the returned data and continues.
"""

import asyncio
import json
import logging

from app.db.tools.transaction_tools import TRANSACTION_TOOLS
from app.lib.tool_schema import registry_tools_to_prompt
from app.llm.client import get_client as get_llm
from app.llm.specs import load
from app.models.state import GraphState

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 3


async def transactions_node(state: GraphState) -> dict:
    event = state.get("event", {})
    user_message = event.get("text", "")
    business_id = state.get("business_id") or event.get("business_id", "")
    thread_id = state.get("thread_id") or event.get("thread_id", "")

    from app.lib.field_formatter import format_user_input
    user_message = format_user_input(user_message)

    # Check if returning from a tool call (db_translator just ran)
    domain_result = state.get("domain_result")
    if domain_result and state.get("return_to") == "transactions":
        summary = domain_result.get("summary", "")
        logger.info(f"Transactions: got tool results back — {summary[:100]}")

        # The DB operation completed — respond with the translated result
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

    config = load("domain/transactions", tools=TRANSACTION_TOOLS)
    llm = get_llm()

    history = state.get("messages", [])
    logger.info(f"Transactions: history has {len(history)} messages, business_id={business_id}")

    llm_with_tools = llm.bind_tools(TRANSACTION_TOOLS)

    system_content = config.system_prompt
    system_content += f"\n\n## Available DB Tools (for tool_requests)\n{registry_tools_to_prompt()}"
    system_content += f"\n\n## Context\n- business_id: {business_id}\n- thread_id: {thread_id}"

    prompt = [{"role": "system", "content": system_content}]
    prompt.extend(history[-12:])
    prompt.append({"role": "user", "content": user_message})

    raw = ""
    for iteration in range(MAX_TOOL_ITERATIONS):
        llm_response = await llm_with_tools.ainvoke(prompt)

        if llm_response.tool_calls:
            logger.info(f"Transactions: calling {len(llm_response.tool_calls)} tool(s): {[tc['name'] for tc in llm_response.tool_calls]}")
            prompt.append({"role": "assistant", "content": llm_response.content or "", "tool_calls": llm_response.tool_calls})

            async def _run_tool(tc):
                name = tc["name"]
                args = dict(tc["args"])
                if "business_id" in args and not args["business_id"]:
                    args["business_id"] = business_id
                res = await _execute_tool(name, args)
                logger.info(f"Transactions: tool {name} returned {len(res)} chars")
                return tc["id"], res

            tool_results = await asyncio.gather(*[_run_tool(tc) for tc in llm_response.tool_calls])

            for call_id, result in tool_results:
                prompt.append({"role": "tool", "tool_call_id": call_id, "content": result})
            continue

        raw = llm_response.content.strip()
        break
    else:
        raw = llm_response.content.strip() if llm_response.content else '{"response": "How can I help with your transactions?", "workflow_status": "completed"}'

    logger.info(f"Transactions raw output: {raw[:200]}")

    parsed = _parse_response(raw)
    text = parsed.get("response", raw)
    fields = parsed.get("fields")

    response_data = {"mode": "conversation", "text": text}
    if fields:
        response_data["input"] = {"fields": fields}

    result = {
        "response": response_data,
        "output_mode": "conversation",
        "workflow_owner": "transactions",
        "current_agent": "transactions",
        "messages": [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": raw},
        ],
    }

    # If the specialist needs DB operations via tool_planner
    tool_requests = parsed.get("tool_requests")
    if tool_requests and isinstance(tool_requests, list):
        result["tool_requests"] = tool_requests
        result["return_to"] = "transactions"
        result["workflow_owner"] = "transactions"

    return result


async def _execute_tool(tool_name: str, tool_args: dict) -> str:
    tool_map = {t.name: t for t in TRANSACTION_TOOLS}
    tool_fn = tool_map.get(tool_name)
    if not tool_fn:
        return f"Unknown tool: {tool_name}"
    try:
        result = await tool_fn.ainvoke(tool_args)
        return str(result)
    except Exception as e:
        logger.warning(f"Transactions tool {tool_name} failed: {e}")
        return f"Tool error: {e}"


def _parse_response(raw: str) -> dict:
    try:
        from app.lib.json_parser import parse_json_output
        return parse_json_output(raw)
    except (json.JSONDecodeError, IndexError, ValueError):
        return {"response": raw.strip(), "workflow_status": "completed"}
