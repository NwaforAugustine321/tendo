"""Onboarding node — handles business profile understanding through conversation."""

import logging

from app.llm.client import get_client as get_llm
from app.llm.specs import load
from app.models.state import GraphState

logger = logging.getLogger(__name__)


async def onboarding_node(state: GraphState) -> dict:
    """
    Collects business information through natural conversation.
    Routes from MOA when user has no business profile yet.
    """
    event = state.get("event", {})
    user_message = event.get("text", "")

    config = load("onboarding")
    llm = get_llm()

    history = state.get("messages", [])

    messages = [
        {"role": "system", "content": config.system_prompt},
    ]
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_message})

    response = await llm.ainvoke(messages)
    assistant_text = response.content

    logger.info(f"Onboarding: {assistant_text[:80]}")

    return {
        "response": {"mode": "conversation", "text": assistant_text},
        "output_mode": "conversation",
        "messages": history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_text},
        ],
    }
