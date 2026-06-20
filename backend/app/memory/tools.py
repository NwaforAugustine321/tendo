"""Memory tools — callable by MOA to fetch context on demand."""

import logging

from langchain_core.tools import tool

from app.config.settings import settings
from app.memory.long_term_mem import ensure_store
from app.memory.retriever import retrieve_relevant_memories
from app.memory.summarizer import get_latest_summary
from app.db.tools.profiles import get_business_profile

logger = logging.getLogger(__name__)

# These will be bound to the LLM as tools MOA can call


@tool
async def recall_summary(business_id: str) -> str:
    """Get the rolling conversation summary for a business. Use this to understand overall context and what happened in previous conversations."""
    try:
        store = await ensure_store()
        summary = await get_latest_summary(store, business_id)
        return summary or "No conversation history found for this business."
    except Exception as e:
        logger.warning(f"recall_summary failed: {e}")
        return "Could not retrieve summary."


@tool
async def search_memory(business_id: str, query: str) -> str:
    """Search past conversations for specific information. Use when you need to find a specific fact, statement, or detail from previous messages."""
    try:
        store = await ensure_store()
        results = await retrieve_relevant_memories(
            store=store,
            query=query,
            business_id=business_id,
            limit=5,
        )
        return results or "No relevant past messages found."
    except Exception as e:
        logger.warning(f"search_memory failed: {e}")
        return "Could not search memory."


@tool
async def get_profile(business_id: str) -> str:
    """Get the current business profile data (name, type, description, phone, location, metadata). Use this to check what's already known about the business."""
    try:
        profile = await get_business_profile(business_id=business_id)
        if profile and isinstance(profile, dict) and not profile.get("error"):
            import json
            exclude = {"id", "user_id", "created_at", "updated_at"}
            data = {k: v for k, v in profile.items() if k not in exclude and v}
            if data.get("logo_url"):
                data["logo"] = "uploaded"
                del data["logo_url"]
            return json.dumps(data) if data else "Profile exists but has no data yet."
        return "No business profile found."
    except Exception as e:
        logger.warning(f"get_profile failed: {e}")
        return "Could not retrieve profile."


# All tools available to MOA
MEMORY_TOOLS = [recall_summary, search_memory, get_profile]
