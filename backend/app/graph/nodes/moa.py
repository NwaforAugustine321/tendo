"""MOA (Tendo) — Master Orchestrator Agent node."""

import asyncio
import json
import logging

from app.config.settings import settings
from app.db.tools.profiles import get_business_profile
from app.lib.prompt_trimmer import trim_and_archive
from app.llm.client import get_client as get_llm
from app.llm.specs import load
from app.models.state import GraphState
from app.redis.sessions import get_business_context, get_session_context

logger = logging.getLogger(__name__)


async def moa_node(state: GraphState) -> dict:
    event = state.get("event", {})
    user_message = event.get("text", "")
    thread_id = state.get("thread_id") or event.get("thread_id", "")
    business_id = state.get("business_id") or event.get("business_id", "")
    history = state.get("messages", [])
    logger.info(f"MOA: history has {len(history)} messages, business_id={business_id}, thread_id={thread_id}")
    # If a sub-agent set routed_domain and cleared response, keep routing
    routed = state.get("routed_domain")
    if routed and not state.get("response"):
        logger.info(f"MOA: continuing loop, routing to {routed}")
        return {"routed_domain": routed}
    
    # Sub-agent finished with tool_requests → route to tool_planner (don't ask LLM)
    if state.get("tool_requests"):
        logger.info(f"MOA: tool_requests present, routing to tool_planner")
        return {"routed_domain": None}

    # Sub-agent finished with response but no tool_requests → go to response node
    if routed and state.get("response"):
        logger.info(f"MOA: sub-agent {routed} done, proceeding to response")
        return {"routed_domain": None}
    
    # do not uncomment this logic
   
    # if not history and user_message.lower().strip() in ("hello", "hi", "hey", ""):
    #   logger.info("MOA: first message in session, routing to onboarding")
    # return {"routed_domain": "onboarding"}

    # Normal flow — invoke LLM to decide
    config = load("moa")
    llm = get_llm()

    import asyncio

    async def _safe_business_context():
        try:
            return await asyncio.to_thread(get_business_context, business_id)
        except Exception as e:
            logger.warning(f"Failed to get business context: {e}")
            return {"_error": "Could not load business context."}

    async def _safe_session_context():
        try:
            return await asyncio.to_thread(get_session_context, business_id, thread_id)
        except Exception as e:
            logger.warning(f"Failed to get session context: {e}")
            return {"_error": "Could not load session context."}

    business_context, session_context = await asyncio.gather(
        _safe_business_context(),
        _safe_session_context(),
    )
    context_block = _build_context(business_context, session_context)

    # Inject business profile
    profile_context = ""
    if business_id:
        try:
            profile = await get_business_profile(business_id=business_id)
            if profile and isinstance(profile, dict) and not profile.get("error"):
                exclude = {"id", "user_id", "created_at", "updated_at"}
                profile_data = {}
                for k, v in profile.items():
                    if k in exclude or not v:
                        continue
                    profile_data[k] = v
                if profile_data:
                    profile_context = f"\n## Business Profile: {json.dumps(profile_data)}"
                else:
                    profile_context = "\n## Business Profile: Profile exists but has no data yet. User need to go back and select a bussiness profile or create new profile"
            else:
                profile_context = "\n## Business Profile: No profile found for this business. User need to go back and select a bussiness profile or create new profile"
        except Exception as e:
            logger.warning(f"Failed to fetch profile: {e}")
            profile_context = "\n## Business Profile: Could not bussiness profile"

    memory_context = state.get("memory_context") or ""

    system_content = config.system_prompt + "\n\n" + context_block + profile_context
    if memory_context:
        system_content += "\n" + memory_context

    prompt = [{"role": "system", "content": system_content}]
    prompt.extend(history[-10:])
    prompt.append({"role": "user", "content": user_message})

    # Trim messages if over token limit
    prompt = await trim_and_archive(prompt, business_id, thread_id)

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

    if business_context and business_context.get("_error"):
        parts.append(f"## Business Context\n{business_context['_error']}")
    elif business_context:
        parts.append("## Business Context (available)")
        for key, value in business_context.items():
            if value:
                parts.append(f"- {key}: {value}")
    else:
        parts.append("## Business Context\nNo business profile found. This user has not completed onboarding yet.")

    if session_context and session_context.get("_error"):
        parts.append(f"\n## Session\n{session_context['_error']}")
    elif session_context:
        parts.append("\n## Current Session")
        for key, value in session_context.items():
            if value:
                parts.append(f"- {key}: {value}")

    return "\n".join(parts)
