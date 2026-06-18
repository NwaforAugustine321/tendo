"""RAG-style retrieval from long-term Store."""

import asyncio
import logging

from langgraph.store.postgres import AsyncPostgresStore

logger = logging.getLogger(__name__)


async def retrieve_relevant_memories(
    store: AsyncPostgresStore,
    query: str,
    business_id: str,
    thread_id: str,
    limit: int = 5,
    timeout: float = 5.0,
) -> str | None:
    """Query Store for semantically similar archived messages.

    Args:
        store: The initialized AsyncPostgresStore.
        query: The user message to find similar memories for.
        business_id: Business scope identifier.
        thread_id: Thread scope identifier.
        limit: Maximum number of items to retrieve.
        timeout: Maximum query time in seconds.

    Returns:
        Formatted string of relevant memories, or None if none found/error.
    """
    namespace = (business_id, thread_id, "archived_messages")

    try:
        results = await asyncio.wait_for(
            store.asearch(namespace, query=query, limit=limit),
            timeout=timeout,
        )

        if not results:
            return None

        # Format results as a single string
        formatted_parts = []
        for item in results[:limit]:
            value = item.value
            role = value.get("role", "unknown")
            content = value.get("content", "")
            timestamp = value.get("timestamp", "")
            formatted_parts.append(f"[{role} @ {timestamp}]: {content}")

        if not formatted_parts:
            return None

        return "\n".join(formatted_parts)

    except asyncio.TimeoutError:
        logger.warning(
            "Store query timed out after %.1fs for thread %s", timeout, thread_id
        )
        return None
    except Exception as e:
        logger.warning("Failed to retrieve memories from store: %s", e)
        return None
