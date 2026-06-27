"""Memory tools — callable by agents to fetch context on demand."""

import json
import logging

from langchain_core.tools import tool

from app.db.tools.profiles import get_business_profile
from app.memory.memory import get_memory

logger = logging.getLogger(__name__)


@tool
async def recall_memory(business_id: str, query: str) -> str:
    """Search past conversations for specific information. Use when you need to find a specific fact, statement, or detail from previous interactions."""
    try:
        memory = get_memory(f"/business/{business_id}")
        matches = await memory.recall(query, limit=5)
        if not matches:
            return "No relevant past memories found."
        return "\n".join(m.format() for m in matches)
    except Exception as e:
        logger.warning(f"recall_memory failed: {e}")
        return "Could not search memory."


@tool
async def get_profile(business_id: str) -> str:
    """Get the current business profile data (name, type, description, phone, location, metadata). Use this to check what's already known about the business."""
    try:
        profile = await get_business_profile(business_id=business_id)
        if profile and isinstance(profile, dict) and not profile.get("error"):
            exclude = {"id", "user_id", "created_at", "updated_at", "onboarding_completed", "logo_url"}
            data = {k: v for k, v in profile.items() if k not in exclude and v}
            return json.dumps(data) if data else "Profile exists but has no data yet."
        return "No business profile found."
    except Exception as e:
        logger.warning(f"get_profile failed: {e}")
        return "Could not retrieve profile."


@tool
async def save_to_memory(business_id: str, contents: list[str]) -> str:
    """Store one or more important facts, decisions, observations, or lessons in memory so they can be recalled later. Pass multiple items at once when you have several things worth remembering."""
    if not contents:
        return "No items provided to save."
    try:
        memory = get_memory(f"/business/{business_id}")
        await memory.remember_many(contents)
        return f"Saved {len(contents)} item(s) to memory."
    except Exception as e:
        logger.warning(f"save_to_memory failed: {e}")
        return f"Could not save to memory: {e}"


# All memory tools available to agents
MEMORY_TOOLS = [recall_memory, get_profile, save_to_memory]
