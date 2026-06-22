"""Response node — polish text for TTS + persist turn to long-term store."""

import logging
import uuid
from datetime import datetime, timezone

from app.llm.client import get_client as get_llm
from app.llm.specs import load
from app.memory.long_term_mem import ensure_store
from app.models.state import GraphState

logger = logging.getLogger(__name__)


async def response_node(state: GraphState) -> dict:
    """Polish response for TTS, format final output, and persist conversation turn."""
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

    # Polish the text through response_generator for TTS readiness
    # NOTE: Disabled — response_generator was stripping question fields and changing types.
    # Re-enable when using a model that reliably preserves JSON structure.
    # if assistant_text and _needs_polishing(assistant_text):
    #     polished = await _polish_response(assistant_text)
    #     if polished:
    #         response["text"] = polished
    #         assistant_text = polished

    # Persist turn to long-term store
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


def _needs_polishing(text: str) -> bool:
    """Check if text has artifacts that need cleaning for TTS."""
    indicators = ["**", "```", "- ", "* ", "#{", '{"', "\\n"]
    return any(ind in text for ind in indicators)


async def _polish_response(text: str) -> str:
    """Run text through the response_generator spec for TTS polishing."""
    try:
        config = load("response_generator")
        llm = get_llm()
        prompt = [
            {"role": "system", "content": config.system_prompt},
            {"role": "user", "content": text},
        ]
        response = await llm.ainvoke(prompt)
        polished = response.content.strip()
        if polished:
            logger.info(f"Response polished: {polished[:80]}")
            return polished
    except Exception as e:
        logger.warning(f"Response polishing failed: {e}")
    return ""
