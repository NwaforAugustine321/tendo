"""Session management service — create and resume conversation sessions."""

import logging

from app.db.tools.sessions import insert_session, find_active_session

logger = logging.getLogger(__name__)


async def create_session(business_id: str, user_id: str, title: str = "Onboarding") -> dict:
    """Create a new conversation session linked to a business and user."""
    return await insert_session(business_id, user_id, title)


async def get_active_session(business_id: str, user_id: str) -> dict | None:
    """Find an existing active session for a business+user pair."""
    return await find_active_session(business_id, user_id)


async def get_or_create_session(business_id: str, user_id: str) -> dict:
    """Get existing active session or create a new one."""
    existing = await get_active_session(business_id, user_id)
    if existing:
        return existing
    return await create_session(business_id, user_id)
