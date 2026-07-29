"""Response node — formats final output, emits to client, and persists turn to LanceDB memory."""

import logging

from app.memory.memory import Memory
from app.models.state import GraphState

logger = logging.getLogger(__name__)


async def response_node(state: GraphState) -> dict:
    """Format final response, emit it to the client via emit_callback, and persist conversation turn."""
    event = state.get("event", {})
    user_message = event.get("text", "")
    thread_id = state.get("thread_id") or event.get("thread_id", "default")
    business_id = state.get("business_id") or event.get("business_id", "default")
    emit_callback = state.get("emit_callback")

    response = state.get("response") or {}
    response_text = response.get("text", "")
    msg_type = response.get("msg_type", "answer")
    questions = response.get("questions")

    # If we have a domain_result summary and no response text yet, use the summary
    domain_result = state.get("domain_result")
    if domain_result and domain_result.get("summary") and not response_text:
        response_text = domain_result["summary"]
        response = {"mode": "conversation", "text": response_text, "msg_type": "answer"}
        msg_type = "answer"

    if not response_text:
        response_text = "I'm here to help. What would you like to know?"

    # --- Emit response to client ---
    if emit_callback:
        try:
            if msg_type == "question" and questions:
                await emit_callback("message", {
                    "type": "message",
                    "data": {"response": response_text, "msg_type": "question", "questions": questions},
                })
            else:
                await emit_callback("message", {
                    "type": "message",
                    "data": {"response": response_text, "msg_type": "answer"},
                })
        except Exception as e:
            logger.error("Failed to emit response to client: %s", e)

    # --- Persist turn to LanceDB memory (conversations table) ---
    if user_message and response_text:
        try:
            memory = Memory(scopes=[f"/business/{business_id}"], business_id=business_id, table_name="conversations")
            content = f"User: {user_message}\nAssistant: {response_text}"
            await memory.remember(
                content=content,
                scope="conversations",
                metadata={"thread_id": thread_id, "business_id": business_id},
            )
            logger.debug("Persisted turn to memory: %s:%s", business_id, thread_id)
        except Exception as e:
            logger.warning("Failed to persist turn to memory: %s", e)

    return {"response": response}
