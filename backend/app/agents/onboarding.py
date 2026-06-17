"""Onboarding agent — handles business profile understanding through conversation."""

import logging

from app.llm.client import get_client as get_llm
from app.llm.specs import load

logger = logging.getLogger(__name__)


async def process(user_message: str, conversation_history: list[dict]) -> str:
    """Process a user message during onboarding and return the agent response."""
    config = load("onboarding")
    llm = get_llm()

    messages = [{"role": "system", "content": config.system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    response = await llm.ainvoke(messages)
    return response.content
