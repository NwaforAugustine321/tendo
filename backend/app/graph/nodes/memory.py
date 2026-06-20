"""Memory node — retrieves conversation context from long-term store."""

import asyncio
import logging

from app.memory.long_term_mem import ensure_store
from app.memory.retriever import retrieve_relevant_memories
from app.memory.summarizer import get_latest_summary
from app.models.state import GraphState

logger = logging.getLogger(__name__)


async def memory_node(state: GraphState) -> dict:
    """Retrieve both summaries and semantic memories in parallel."""
    event = state.get("event", {})
    user_message = event.get("text", "")
    thread_id = state.get("thread_id") or event.get("thread_id", "")
    business_id = state.get("business_id") or event.get("business_id", "")

    summary_text = ""
    semantic_text = ""

    if user_message and business_id:
        try:
            store = await ensure_store()

            # Fetch summary and semantic results in parallel
            summary_task = get_latest_summary(store, business_id, limit=2)
            semantic_task = retrieve_relevant_memories(
                store=store,
                query=user_message,
                business_id=business_id,
                limit=5,
            )

            summary_text, semantic_text = await asyncio.gather(
                summary_task, semantic_task
            )
        except Exception as e:
            logger.warning("Failed to retrieve memories: %s", e)

    # Build combined memory context
    parts = []
    if summary_text:
        parts.append(f"## Conversation History Summary\n{summary_text}")
    if semantic_text:
        parts.append(f"## Relevant Past Context\n{semantic_text}")

    memory_context = "\n\n".join(parts) if parts else ""

    if memory_context:
        logger.info("Memory: retrieved summary + semantic context for %s", business_id)
    else:
        logger.info("Memory: no context found for %s", business_id)

    return {
        "memory_context": memory_context,
        "thread_id": thread_id,
        "business_id": business_id,
    }
