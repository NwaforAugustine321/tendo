"""MOA (Tendo) — Master Orchestrator Agent.

Orchestrates the conversation flow:
1. Loads business context from cache
2. Decides context sufficiency
3. Routes to sub-agents or responds directly
4. Produces routing decisions for the graph workflow
"""

import logging
from typing import Literal

from app.llm.client import get_client as get_llm
from app.llm.specs import load
from app.redis.sessions import get_business_context, get_session_context

logger = logging.getLogger(__name__)


async def process(
    user_message: str,
    thread_id: str,
    business_id: str,
    conversation_history: list[dict],
) -> dict:
    """
    Process a user message and return a routing decision.

    Returns dict with:
      - response: str (text to send to user, if responding directly)
      - route: str | None (next node to route to: tool_planner, domain_router, option_generator, confirmation)
      - intent: str | None (parsed intent for downstream agents)
      - tool_requests: list | None (if routing to tool_planner)
      - routed_domain: str | None (if routing to domain agent: sales/payment/inventory/service)
    """
    config = load("moa")
    llm = get_llm()

    # Load cached context
    business_context = get_business_context(business_id)
    session_context = get_session_context(business_id, thread_id)

    # Build system prompt with context
    context_block = _build_context_block(business_context, session_context)

    messages = [
        {"role": "system", "content": config.system_prompt + "\n\n" + context_block},
    ]
    messages.extend(conversation_history[-10:])
    messages.append({"role": "user", "content": user_message})

    response = await llm.ainvoke(messages)
    assistant_text = response.content

    # For now, MOA responds directly (routing will be added when sub-agents are connected)
    return {
        "response": assistant_text,
        "route": None,
        "intent": None,
        "tool_requests": None,
        "routed_domain": None,
    }


def _build_context_block(business_context: dict | None, session_context: dict | None) -> str:
    """Build a context block to inject into the system prompt."""
    parts = []

    if business_context:
        parts.append("## Business Context (from cache)")
        for key, value in business_context.items():
            if value:
                parts.append(f"- {key}: {value}")

    if session_context:
        parts.append("\n## Current Session")
        for key, value in session_context.items():
            if value:
                parts.append(f"- {key}: {value}")

    if not parts:
        parts.append("## Context\nNo business context available yet. This may be a new user.")

    return "\n".join(parts)
