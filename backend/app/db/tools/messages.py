"""Conversation message persistence — save and fetch from conversation_messages table."""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.db.client import get_client

logger = logging.getLogger(__name__)


async def save_messages(
    business_id: str,
    session_id: str,
    messages: list[dict],
    record_id: str | None = None,
) -> None:
    """Insert messages into the conversation_messages table."""
    if not session_id or not business_id:
        logger.warning("[save_messages] Missing session_id or business_id — skipping")
        return

    rows = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role not in ("user", "assistant", "system") or not content:
            continue

        # Clean up JSON-wrapped assistant responses
        if role == "assistant" and content.strip().startswith("{"):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and parsed.get("response"):
                    content = parsed["response"]
            except (json.JSONDecodeError, ValueError):
                pass

        row = {
            "session_id": session_id,
            "business_id": business_id,
            "role": role,
            "content": content,
        }
        if record_id:
            row["record_id"] = record_id
        rows.append(row)

    if not rows:
        logger.warning("[save_messages] No valid messages to save")
        return

    try:
        client = get_client()
        result = client.table("conversation_messages").insert(rows).execute()
        logger.info(f"[save_messages] Saved {len(rows)} messages to session={session_id}")
    except Exception as e:
        logger.error(f"[save_messages] FAILED for session={session_id}: {e}")


async def save_message(
    business_id: str,
    session_id: str,
    role: str,
    content: str,
    message_type: str = "text",
    metadata: dict[str, Any] | None = None,
    record_id: str | None = None,
) -> dict | None:
    """Save a single message to the conversation_messages table."""
    if not session_id or not business_id or not content:
        logger.warning(f"[save_message] Missing required fields — session={session_id}, business={business_id}")
        return None

    try:
        client = get_client()
        row = {
            "session_id": session_id,
            "business_id": business_id,
            "role": role,
            "content": content,
            "message_type": message_type,
            "metadata": metadata or {},
        }
        if record_id:
            row["record_id"] = record_id
        result = client.table("conversation_messages").insert(row).execute()
        logger.info(f"[save_message] Saved {role} message to session={session_id}")
        if result.data:
            return result.data[0]
    except Exception as e:
        logger.error(f"[save_message] FAILED: {e}")
    return None


async def fetch_messages(
    business_id: str,
    session_id: str,
    limit: int = 20,
    offset: int = 0,
    record_id: str | None = None,
) -> list[dict]:
    """Fetch messages from conversation_messages table by session_id (and optionally record_id)."""
    try:
        client = get_client()
        query = (
            client.table("conversation_messages")
            .select("role, content, created_at")
            .eq("session_id", session_id)
            .eq("business_id", business_id)
        )

        if record_id:
            query = query.eq("record_id", record_id)

        query = query.order("created_at", desc=False)

        if offset > 0:
            query = query.range(offset, offset + limit - 1)
        else:
            query = query.limit(limit)

        result = query.execute()

        if not result.data:
            logger.info(f"[fetch_messages] No messages found for session={session_id}")
            return []

        logger.info(f"[fetch_messages] Fetched {len(result.data)} messages for session={session_id}")
        return [{"role": m["role"], "content": m["content"]} for m in result.data]

    except Exception as e:
        logger.error(f"[fetch_messages] FAILED for session={session_id}: {e}")
        return []
