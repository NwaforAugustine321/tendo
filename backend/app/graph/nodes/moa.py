"""MOA (Tendo) — Master Orchestrator Agent node."""

import logging

from app.llm.client import get_client as get_llm
from app.llm.specs import load
from app.models.state import GraphState
from app.redis.sessions import get_business_context, get_session_context

logger = logging.getLogger(__name__)


async def moa_node(state: GraphState) -> dict:
    """
    Orchestrates the conversation:
    1. Loads BCC + session context
    2. If no business profile → route to onboarding
    3. Otherwise → decide sufficiency and respond or route
    """
    event = state.get("event", {})
    user_message = event.get("text", "")
    thread_id = event.get("thread_id", "default")
    business_id = event.get("business_id", "default")

    business_context = get_business_context(business_id)
    session_context = get_session_context(business_id, thread_id)

    # No business profile → delegate to onboarding agent
    if not business_context:
        logger.info("No business context — routing to onboarding")
        return {
            "routed_domain": "onboarding",
            "event": event,
            "messages": state.get("messages", []),
        }

    # Has business profile → MOA handles directly
    config = load("moa")
    llm = get_llm()

    context_block = _build_context(business_context, session_context)
    history = state.get("messages", [])

    messages = [
        {"role": "system", "content": config.system_prompt + "\n\n" + context_block},
    ]
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_message})

    response = await llm.ainvoke(messages)
    assistant_text = response.content

    logger.info(f"MOA: {assistant_text[:80]}")

    return {
        "response": {"mode": "conversation", "text": assistant_text},
        "output_mode": "conversation",
        "messages": history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_text},
        ],
    }


def _build_context(business_context: dict | None, session_context: dict | None) -> str:
    parts = []

    if business_context:
        parts.append("## Business Context")
        for key, value in business_context.items():
            if value:
                parts.append(f"- {key}: {value}")

    if session_context:
        parts.append("\n## Current Session")
        for key, value in session_context.items():
            if value:
                parts.append(f"- {key}: {value}")

    return "\n".join(parts) if parts else ""
