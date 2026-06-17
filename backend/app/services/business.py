"""Business profile service."""

import logging
from app.db.tools.profiles import get_business_profiles

logger = logging.getLogger(__name__)


async def list_business_profiles(user_id: str) -> list[dict]:
    try:
        return await get_business_profiles(user_id)
    except Exception as e:
        logger.error(f"Failed to get business profiles: {e}")
        return []
