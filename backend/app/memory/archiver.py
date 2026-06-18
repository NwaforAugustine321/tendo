"""Archive trimmed messages to long-term Store."""

import logging
import uuid
from datetime import datetime, timezone

from langgraph.store.postgres import AsyncPostgresStore

logger = logging.getLogger(__name__)


async def archive_messages(
    store: AsyncPostgresStore,
    messages: list[dict],
    business_id: str,
    thread_id: str,
) -> bool:
    """Write trimmed messages to Store under scoped namespace.

    Namespace: (business_id, thread_id, "archived_messages")

    Each message stored with:
        - role, content, timestamp, thread_id, business_id

    Args:
        store: The initialized AsyncPostgresStore.
        messages: Messages to archive.
        business_id: Business scope identifier.
        thread_id: Thread scope identifier.

    Returns:
        True if archival succeeded, False on failure.
    """
    if not messages:
        return True

    namespace = (business_id, thread_id, "archived_messages")
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        for msg in messages:
            key = str(uuid.uuid4())
            value = {
                "role": msg.get("role", ""),
                "content": msg.get("content", ""),
                "timestamp": timestamp,
                "thread_id": thread_id,
                "business_id": business_id,
            }
            await store.aput(namespace, key, value)

        logger.info(
            "Archived %d messages to long-term store for thread %s",
            len(messages),
            thread_id,
        )
        return True
    except Exception as e:
        logger.error("Failed to archive messages to store: %s", e)
        return False
