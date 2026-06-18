"""Session database operations."""

import logging

from app.db.client import get_client

logger = logging.getLogger(__name__)


async def insert_session(business_id: str, user_id: str, title: str = "Onboarding") -> dict:
    """Insert a new conversation_sessions row."""
    client = get_client()
    data = {
        "business_id": business_id,
        "user_id": user_id,
        "title": title,
        "status": "active",
    }
    result = client.table("conversation_sessions").insert(data).execute()
    if result.data:
        return result.data[0]
    raise Exception("Failed to create session")


async def find_active_session(business_id: str, user_id: str) -> dict | None:
    """Find an existing active session for a business+user pair."""
    client = get_client()
    result = (
        client.table("conversation_sessions")
        .select("*")
        .eq("business_id", business_id)
        .eq("user_id", user_id)
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None
