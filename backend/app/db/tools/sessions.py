"""Session database operations."""

import logging

from app.db.client import get_client

logger = logging.getLogger(__name__)


async def insert_session(business_id: str, user_id: str, title: str = "New Session") -> dict:
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


async def list_sessions(business_id: str, user_id: str, limit: int = 20) -> list[dict]:
    """List all sessions for a business+user, most recent first."""
    client = get_client()
    result = (
        client.table("conversation_sessions")
        .select("id, title, status, created_at, updated_at")
        .eq("business_id", business_id)
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


async def get_session(session_id: str) -> dict | None:
    """Get a single session by ID."""
    client = get_client()
    result = (
        client.table("conversation_sessions")
        .select("*")
        .eq("id", session_id)
        .single()
        .execute()
    )
    return result.data if result.data else None


async def update_session_title(session_id: str, title: str) -> dict:
    """Update session title."""
    client = get_client()
    result = (
        client.table("conversation_sessions")
        .update({"title": title})
        .eq("id", session_id)
        .execute()
    )
    return result.data[0] if result.data else {"error": "Update failed"}
