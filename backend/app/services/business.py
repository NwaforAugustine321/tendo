"""Business profile service — orchestrates operations."""

import logging

from app.db.tools.profiles import (
    get_business_profiles,
    get_business_profile,
    insert_empty_business_profile,
    update_business_profile,
    delete_business_profile,
)
from app.services.session import create_session, get_or_create_session

logger = logging.getLogger(__name__)


async def list_profiles(user_id: str) -> list[dict]:
    """Get all business profiles for a user."""
    try:
        return await get_business_profiles(user_id)
    except Exception as e:
        logger.error(f"Failed to get business profiles: {e}")
        return []


async def get_profile(business_id: str) -> dict:
    """Get a single business profile by ID."""
    return await get_business_profile(business_id)


async def create_empty_profile(user_id: str) -> dict:
    """Create an empty business profile + session."""
    profile = await insert_empty_business_profile(user_id)
    business_id = profile["id"]

    session = await create_session(business_id, user_id)
    session_id = session["id"]

    return {"business_id": business_id, "session_id": session_id}


async def update_profile(business_id: str, updates: dict) -> dict:
    """Update a business profile."""
    if not updates:
        return {"error": "No valid fields to update"}
    return await update_business_profile(business_id, **updates)


async def delete_profile(business_id: str, user_id: str) -> dict:
    """Delete an incomplete business profile."""
    return await delete_business_profile(business_id, user_id)


async def resume_session(business_id: str, user_id: str) -> dict:
    """Get or create a session for an existing business."""
    session = await get_or_create_session(business_id, user_id)
    return {"session_id": session["id"], "business_id": business_id}
