"""Business profile service."""

import logging
from app.db.client import get_client

logger = logging.getLogger(__name__)


async def get_profiles(user_id: str) -> list[dict]:
    """Get all business profiles for a user."""
    try:
        client = get_client()
        result = client.table("users").select("*").eq("id", user_id).execute()
        if result.data:
            return result.data
        return []
    except Exception as e:
        logger.error(f"Failed to get profiles: {e}")
        return []
