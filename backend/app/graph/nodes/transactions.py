"""Transactions agent node — handles transaction-related operations."""

import asyncio
import json
import logging

from app.lib.tool_schema import registry_tools_to_prompt
from app.llm.client import get_client as get_llm
from app.llm.specs import load
from app.lib.prompt_trimmer import trim_and_archive
from app.memory.tools import MEMORY_TOOLS
from app.models.state import GraphState

logger = logging.getLogger(__name__)

TRANSACTION_TOOLS = MEMORY_TOOLS
MAX_TOOL_ITERATIONS = 3


async def transactions_node(state: GraphState) -> dict:
    event = state.get("event", {})
    user_message = event.get("text", "")
    business_id = state.get("business_id") or event.get("business_id", "")
    thread_id = state.get("thread_id") or event.get("thread_id", "")

    config = load("domain/transactions", tools=TRANSACTION_TOOLS)
    llm = get_llm()

    history = state.get("messages", [])
    logger.info(f"Transactions: history has {len(history)} messages, business_id={business_id}")

    llm_with_tools = llm.bind_tools(TRANSACTION_TOOLS)

    system_content = config.system_prompt
    system_content += f"\n\n## Available DB Tools (for tool_requests)\n{registry_tools_to_prompt()}"
    system_content += f"\n\n## Context\n- business_id: {business_id}\n- thread_id: {thread_id}"

    prompt = [{"role": "system", "content": system_content}]
    prompt.extend(history[-10:])
    prompt.append({"role": "user", "content": user_message})

    prompt = await trim_and_archive(prompt, business_id, thread_id)

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
        raw = llm_response.content.strip() if llm_response.content else '{"response": "How can I help with your transactions?", "type": "answer"}'

    logger.info(f"Transactions raw output: {raw[:200]}")

    parsed = _parse_response(raw)
    text = parsed.get("response", raw)
    questions = parsed.get("questions")

    response_data = {"mode": "conversation", "text": text}
    if questions:
        response_data["input"] = questions

    result = {
        "response": response_data,
        "output_mode": "conversation",
        "routed_domain": None,
        "messages": [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": raw},
        ],
    }

    tool_requests = parsed.get("tool_requests")
    if tool_requests and isinstance(tool_requests, list):
        result["tool_requests"] = tool_requests

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
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        if clean.startswith("{"):
            depth = 0
            for i, ch in enumerate(clean):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return json.loads(clean[: i + 1])
        return json.loads(clean)
    except (json.JSONDecodeError, IndexError, ValueError):
        return {"response": raw, "type": "answer"}
