"""MOA (Tendo) — Master Orchestrator Agent with memory tools."""

import asyncio
import json
import logging

from app.config.settings import settings
from app.db.tools.profiles import get_business_profile
from app.lib.prompt_trimmer import trim_and_archive
from app.lib.tool_schema import registry_tool_names, tools_to_prompt
from app.llm.client import get_client as get_llm
from app.llm.specs import load
from app.memory.tools import MEMORY_TOOLS
from app.models.state import GraphState

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 5


async def moa_node(state: GraphState) -> dict:
    event = state.get("event", {})
    user_message = event.get("text", "")
    thread_id = state.get("thread_id") or event.get("thread_id", "")
    business_id = state.get("business_id") or event.get("business_id", "")
    history = state.get("messages", [])

    logger.info(f"MOA: history has {len(history)} messages, business_id={business_id}, thread_id={thread_id}")

    # Pass-through checks (no LLM needed)
    routed = state.get("routed_domain")
    if routed and not state.get("response"):
        logger.info(f"MOA: continuing loop, routing to {routed}")
        return {"routed_domain": routed}

    if state.get("tool_requests"):
        logger.info("MOA: tool_requests present, routing to tool_planner")
        return {"routed_domain": None}

    if routed and state.get("response"):
        logger.info(f"MOA: sub-agent {routed} done, proceeding to response")
        return {"routed_domain": None}

    # Normal flow — invoke LLM with tool-calling
    config = load("moa")
    llm = get_llm()

    # Bind memory tools to the LLM
    llm_with_tools = llm.bind_tools(MEMORY_TOOLS)

    system_content = config.system_prompt
    system_content += f"\n\n## Available Memory Tools\n{tools_to_prompt(MEMORY_TOOLS)}"
    db_tools = registry_tool_names()
    system_content += f"\n\n## Available DB Tools (routed via tool_planner)\n{', '.join(db_tools)}"
    system_content += f"\n\n## Current Context\n- business_id: {business_id}\n- thread_id: {thread_id}"

    prompt = [{"role": "system", "content": system_content}]
    prompt.extend(history[-10:])
    prompt.append({"role": "user", "content": user_message})

    # Trim if needed
    prompt = await trim_and_archive(prompt, business_id, thread_id)

    # Tool-calling loop — MOA can call tools and get results before responding
    for iteration in range(MAX_TOOL_ITERATIONS):
        response = await llm_with_tools.ainvoke(prompt)

        # Check if the LLM wants to call tools
        if response.tool_calls:
            logger.info(f"MOA: calling {len(response.tool_calls)} tool(s): {[tc['name'] for tc in response.tool_calls]}")

            # Add assistant message with tool calls
            prompt.append({"role": "assistant", "content": response.content or "", "tool_calls": response.tool_calls})

            # Execute tools in parallel
            async def _run_tool(tc):
                name = tc["name"]
                args = dict(tc["args"])
                if "business_id" in args and not args["business_id"]:
                    args["business_id"] = business_id
                res = await _execute_tool(name, args)
                logger.info(f"MOA: tool {name} returned {len(res)} chars")
                return tc["id"], res

            tool_results = await asyncio.gather(*[_run_tool(tc) for tc in response.tool_calls])

            for call_id, result in tool_results:
                prompt.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result,
                })

            # Continue loop — LLM will see tool results and decide what to do next
            continue

        # No tool calls — LLM is ready to respond
        raw = response.content.strip()
        break
    else:
        # Exceeded max iterations — use last response
        raw = response.content.strip() if response.content else '{"response": "Let me help you with that.", "type": "answer"}'

    logger.info(f"MOA raw LLM output: {raw[:200]}")

    decision = _parse_decision(raw)

    # If parsing failed, retry once
    if decision.get("_retry"):
        logger.warning("MOA: invalid JSON output, retrying...")
        prompt.append({"role": "assistant", "content": raw})
        prompt.append({"role": "user", "content": "Respond ONLY with a valid JSON object."})
        retry_response = await llm_with_tools.ainvoke(prompt)
        raw = retry_response.content.strip()
        logger.info(f"MOA retry output: {raw[:200]}")
        decision = _parse_decision(raw)
        if decision.get("_retry"):
            decision = {"response": raw, "type": "answer"}

    output_type = decision.get("type", "answer")
    text = decision.get("response", raw)
    target = decision.get("target")
    questions = decision.get("questions")

    logger.info(f"MOA decision: type={output_type}, target={target}")

    new_messages = [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": text},
    ]

    if output_type == "route" and target:
        return {
            "routed_domain": target,
            "response": {"mode": "conversation", "text": text},
            "output_mode": "conversation",
            "messages": new_messages,
        }

    response_data = {"mode": "conversation", "text": text}
    if questions:
        response_data["input"] = questions

    result = {
        "routed_domain": None,
        "response": response_data,
        "output_mode": "conversation",
        "messages": new_messages,
    }

    if output_type == "question" and questions:
        result["interruption"] = {
            "source": "moa",
            "type": "input_required",
            "text": text,
            "input": questions,
        }

    return result


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
        logger.warning(f"Tool {tool_name} failed: {e}")
        return f"Tool error: {e}"


def _parse_decision(raw: str) -> dict:
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(clean)
    except (json.JSONDecodeError, IndexError, ValueError):
        return {"response": raw, "type": "answer", "_retry": True}
