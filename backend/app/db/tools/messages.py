"""Conversation message persistence — save and fetch from conversation_messages table."""

import json
import logging
from typing import Any

from app.db.client import get_client

logger = logging.getLogger(__name__)


async def save_message(
    business_id: str,
    session_id: str,
    role: str,
    content: str,
    message_type: str = "text",
    metadata: dict[str, Any] | None = None,
) -> dict | None:
    """Save a conversation message to the database.

    Args:
        business_id: The business profile ID.
        session_id: The conversation session ID.
        role: Message role ('user' or 'assistant').
        content: Message content text.
        message_type: Type of message (default 'text').
        metadata: Optional metadata dict.

    Returns:
        The saved message record, or None on failure.
    """
    try:
        client = get_client()
        data = {
            "business_id": business_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "message_type": message_type,
            "metadata": metadata or {},
        }
        result = client.table("conversation_messages").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.warning(f"save_message failed: {e}")
        return None


async def save_messages(
    business_id: str,
    session_id: str,
    messages: list[dict],
) -> None:
    """Save multiple conversation messages to the database.

    Args:
        business_id: The business profile ID.
        session_id: The conversation session ID.
        messages: List of message dicts with 'role' and 'content' keys.
    """
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            metadata = {}
            # Store workflow_status in metadata if present in content (JSON)
            if role == "assistant" and content.strip().startswith("{"):
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        ws = parsed.get("workflow_status")
                        if ws:
                            metadata["workflow_status"] = ws
                        resp = parsed.get("response")
                        if resp:
                            content = resp  # Store human-readable text, not raw JSON
                except (json.JSONDecodeError, ValueError):
                    pass
            await save_message(business_id, session_id, role, content, metadata=metadata)


async def fetch_messages(
    business_id: str,
    session_id: str,
    limit: int = 10,
    offset: int = 0,
) -> list[dict]:
    """Fetch the most recent conversation messages from the database.

    Args:
        business_id: The business profile ID.
        session_id: The conversation session ID.
        limit: Maximum number of messages to return.
        offset: Number of messages to skip (for pagination).

    Returns:
        List of message dicts with 'role' and 'content', ordered oldest first (chronological).
    """
    try:
        client = get_client()
        query = (
            client.table("conversation_messages")
            .select("role, content, metadata, created_at")
            .eq("business_id", business_id)
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .limit(limit)
        )

        result = query.execute()
        messages = result.data or []
        # Reverse to get chronological order (oldest first)
        messages.reverse()
        return [{"role": m["role"], "content": m["content"], "metadata": m.get("metadata", {})} for m in messages]
    except Exception as e:
        logger.warning(f"fetch_messages failed: {e}")
        return []


def get_pending_question(messages: list[dict]) -> str | None:
    """Derive pending_question from the last assistant message.

    Checks if the last assistant message had workflow_status=waiting_for_user
    in its metadata (set during save_messages).

    If the very last message is from the user, there's no pending question
    (the user already replied).

    Args:
        messages: List of message dicts (with optional 'metadata' key).

    Returns:
        The question text if the last assistant message was waiting_for_user
        AND no user message came after it, else None.
    """
    if not messages:
        return None

    # If the last message is from the user, they already replied — no pending question
    if messages[-1].get("role") == "user":
        return None

    # Find the last assistant message
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            metadata = msg.get("metadata", {})
            if isinstance(metadata, dict) and metadata.get("workflow_status") == "waiting_for_user":
                return msg.get("content", "")
            # Last assistant message was not waiting — no pending question
            return None

    return None
