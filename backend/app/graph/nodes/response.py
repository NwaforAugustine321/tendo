"""Response node — final output + persist turn to LangGraph Store."""

import logging
import uuid
from datetime import datetime, timezone

from app.memory.long_term_mem import ensure_store
from app.models.state import GraphState

logger = logging.getLogger(__name__)


async def response_node(state: GraphState) -> dict:
    """Persist conversation turn to long-term Store and return final response."""
    event = state.get("event", {})
    user_message = event.get("text", "")
    thread_id = state.get("thread_id") or event.get("thread_id", "default")
    business_id = state.get("business_id") or event.get("business_id", "default")

    response = state.get("response") or {}
    assistant_text = response.get("text", "")

    if user_message and assistant_text:
        try:
            store = await ensure_store()
            namespace = (business_id, thread_id, "conversation_turns")
            key = str(uuid.uuid4())
            value = {
                "user_message": user_message,
                "assistant_message": assistant_text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "thread_id": thread_id,
                "business_id": business_id,
            }
            await store.aput(namespace, key, value)
            logger.info("Persisted turn to store: %s:%s", business_id, thread_id)
        except Exception as e:
            logger.warning("Failed to persist turn to store: %s", e)

    return {"response": response}
