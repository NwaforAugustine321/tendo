"""Memory node — retrieves relevant conversation context from LangGraph Store."""

import logging

from app.memory.long_term_mem import ensure_store
from app.memory.retriever import retrieve_relevant_memories
from app.models.state import GraphState

logger = logging.getLogger(__name__)


async def memory_node(state: GraphState) -> dict:
    """Retrieve relevant memories from long-term store via semantic search."""
    event = state.get("event", {})
    user_message = event.get("text", "")
    thread_id = state.get("thread_id") or event.get("thread_id", "default")
    business_id = state.get("business_id") or event.get("business_id", "default")

    memory_context = None
    if user_message:
        try:
            store = await ensure_store()
            memory_context = await retrieve_relevant_memories(
                store=store,
                query=user_message,
                business_id=business_id,
                thread_id=thread_id,
                limit=5,
            )
        except Exception as e:
            logger.warning("Failed to retrieve memories: %s", e)

    if memory_context:
        memory_context = "\n## Relevant Memory\n" + memory_context
        logger.info("Memory: retrieved relevant context for %s:%s", business_id, thread_id)
    else:
        memory_context = ""
        logger.info("Memory: no relevant context found for %s:%s", business_id, thread_id)

    return {
        "memory_context": memory_context,
        "thread_id": thread_id,
        "business_id": business_id,
    }
