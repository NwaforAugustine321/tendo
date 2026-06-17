"""MOA (Tendo) — Master Orchestrator Agent node."""

import json
import logging

from app.llm.client import get_client as get_llm
from app.llm.specs import load
from app.models.state import GraphState
from app.redis.sessions import get_business_context, get_session_context

logger = logging.getLogger(__name__)


async def moa_node(state: GraphState) -> dict:
    event = state.get("event", {})
    user_message = event.get("text", "")
    thread_id = event.get("thread_id", "default")
    business_id = event.get("business_id", "default")

    config = load("moa")
    llm = get_llm()

    business_context = get_business_context(business_id)
    session_context = get_session_context(business_id, thread_id)
    context_block = _build_context(business_context, session_context)

    history = state.get("messages", [])

    messages = [
        {"role": "system", "content": config.system_prompt + "\n\n" + context_block},
    ]
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_message})

    response = await llm.ainvoke(messages)
    raw = response.content.strip()

    # Parse LLM routing decision
    decision = _parse_decision(raw)
    action = decision.get("action", "respond")
    text = decision.get("text", raw)
    target = decision.get("target")

    logger.info(f"MOA decision: action={action}, target={target}")

    if action == "route" and target:
        return {
            "routed_domain": target,
            "response": {"mode": "conversation", "text": text},
            "output_mode": "conversation",
            "event": event,
            "messages": history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": text},
            ],
        }

    return {
        "response": {"mode": "conversation", "text": text},
        "output_mode": "conversation",
        "messages": history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": text},
        ],
    }


def _parse_decision(raw: str) -> dict:
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(clean)
    except (json.JSONDecodeError, IndexError):
        return {"action": "respond", "text": raw}


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
