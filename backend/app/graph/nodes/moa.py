"""MOA (Tendo) — Master Orchestrator Agent node."""

import json
import logging

from app.config.settings import settings
from app.llm.client import get_client as get_llm
from app.llm.specs import load
from app.memory.archiver import archive_messages
from app.memory.long_term_mem import ensure_store
from app.memory.trimmer import count_tokens, trim_messages_to_limit
from app.models.state import GraphState
from app.redis.sessions import get_business_context, get_session_context

logger = logging.getLogger(__name__)


async def moa_node(state: GraphState) -> dict:
    event = state.get("event", {})
    user_message = event.get("text", "")
    thread_id = state.get("thread_id") or event.get("thread_id", "default")
    business_id = state.get("business_id") or event.get("business_id", "default")

    # If a sub-agent set routed_domain and cleared response, keep routing
    routed = state.get("routed_domain")
    if routed and not state.get("response"):
        logger.info(f"MOA: continuing loop, routing to {routed}")
        return {"routed_domain": routed}
    
    # Sub-agent finished (routed_domain still set from previous state + response exists).
    # MOA doesn't invoke LLM here — just passes through.
    # If tool_requests exist: route_from_moa will send to tool_planner/db_oracle to save.
    # If no tool_requests: route_from_moa will send to response node to show the message.
    if routed and state.get("response"):
        if state.get("tool_requests"):
            logger.info(f"MOA: sub-agent {routed} done with tool_requests, routing to tool_planner")
            return {"routed_domain": None}
        logger.info(f"MOA: sub-agent {routed} done, proceeding to response")
        return {"routed_domain": None}

    # If this is the first message in a session (no history), always start with onboarding
    history = state.get("messages", [])
    if not history and user_message.lower().strip() in ("hello", "hi", "hey", ""):
        logger.info("MOA: first message in session, routing to onboarding")
        return {"routed_domain": "onboarding"}

    # Normal flow — invoke LLM to decide
    config = load("moa")
    llm = get_llm()

    business_context = get_business_context(business_id)
    session_context = get_session_context(business_id, thread_id)
    context_block = _build_context(business_context, session_context)

    memory_context = state.get("memory_context") or ""

    system_content = config.system_prompt + "\n\n" + context_block
    if memory_context:
        system_content += "\n" + memory_context

    prompt = [{"role": "system", "content": system_content}]
    prompt.extend(history[-10:])
    prompt.append({"role": "user", "content": user_message})

    # Trim messages if token count exceeds the configured limit
    token_limit = settings.max_message_token_size
    if count_tokens(prompt) > token_limit:
        trim_result = trim_messages_to_limit(prompt, token_limit)
        if trim_result.trimmed_messages:
            # Archive trimmed messages to long-term store
            try:
                store = await ensure_store()
                archived = await archive_messages(
                    store=store,
                    messages=trim_result.trimmed_messages,
                    business_id=business_id,
                    thread_id=thread_id,
                )
            except Exception as e:
                logger.warning("Failed to get store for archival: %s", e)
                archived = False

            if archived:
                prompt = trim_result.retained_messages
                logger.info(
                    "Trimmed %d messages before LLM call for %s:%s",
                    len(trim_result.trimmed_messages),
                    business_id,
                    thread_id,
                )
            else:
                # Archival failed — retain all messages (don't trim)
                logger.warning("Archival failed, retaining all messages")

    llm_response = await llm.ainvoke(prompt)
    raw = llm_response.content.strip()

    logger.info(f"MOA raw LLM output: {raw[:200]}")

    decision = _parse_decision(raw)
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

    return {
        "routed_domain": None,
        "response": response_data,
        "output_mode": "conversation",
        "messages": new_messages,
    }


def _parse_decision(raw: str) -> dict:
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
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


def _build_context(business_context: dict | None, session_context: dict | None) -> str:
    parts = []

    if business_context:
        parts.append("## Business Context (available)")
        for key, value in business_context.items():
            if value:
                parts.append(f"- {key}: {value}")
    else:
        parts.append("## Business Context\nNo business profile found. This user has not completed onboarding yet.")

    if session_context:
        parts.append("\n## Current Session")
        for key, value in session_context.items():
            if value:
                parts.append(f"- {key}: {value}")

    return "\n".join(parts)
