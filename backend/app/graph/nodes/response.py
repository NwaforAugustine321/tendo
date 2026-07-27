"""Response node — polish text for TTS + persist turn to LanceDB memory."""

import logging

from app.memory.memory import Memory
from app.models.state import GraphState

logger = logging.getLogger(__name__)


async def response_node(state: GraphState) -> dict:
    """Polish response for TTS, format final output, and persist conversation turn to memory."""
    event = state.get("event", {})
    user_message = event.get("text", "")
    thread_id = state.get("thread_id") or event.get("thread_id", "default")
    business_id = state.get("business_id") or event.get("business_id", "default")

    response = state.get("response") or {}
    assistant_text = response.get("text", "")

    # If we have a domain_result summary and no response text yet, use the summary
    domain_result = state.get("domain_result")
    if domain_result and domain_result.get("summary") and not assistant_text:
        assistant_text = domain_result["summary"]
        response = {"mode": "conversation", "text": assistant_text}

    # Persist turn to LanceDB memory
    if user_message and assistant_text:
        try:
            memory = Memory(scopes=[f"/business/{business_id}"], business_id=business_id)
            content = f"User: {user_message}\nAssistant: {assistant_text}"
            await memory.remember(
                content=content,
                scope="conversations",
                metadata={"thread_id": thread_id, "business_id": business_id},
            )
            logger.debug("Persisted turn to memory: %s:%s", business_id, thread_id)
        except Exception as e:
            logger.warning("Failed to persist turn to memory: %s", e)

    return {"response": response}
