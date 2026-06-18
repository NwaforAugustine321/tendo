"""Business profile service."""

import logging

from app.db.tools.profiles import (
    get_business_profiles,
    insert_empty_business_profile,
)

logger = logging.getLogger(__name__)


async def list_business_profiles(user_id: str) -> list[dict]:
    try:
        return await get_business_profiles(user_id)
    except Exception as e:
        logger.error(f"Failed to get business profiles: {e}")
        return []


async def create_empty_business_profile(user_id: str) -> dict:
    """Create an empty business profile with onboarding_completed=false."""
    return await insert_empty_business_profile(user_id)
