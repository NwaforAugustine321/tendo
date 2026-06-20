"""Conversation summarizer — compresses old messages into a compact summary."""

import logging
import uuid
from datetime import datetime, timezone

from langgraph.store.postgres import AsyncPostgresStore

from app.llm.client import get_client as get_llm

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = """Summarize this conversation concisely. Extract and preserve:
- All facts, data points, and information shared
- Decisions made or actions taken
- Current state of any task or workflow in progress
- User preferences, corrections, or instructions
- Any pending questions or next steps
- All knowledge and understanding

Write in past tense. Be factual and compact. Under 200 words.

Conversation:
{messages}

If there was a previous summary, integrate new information with it:
{previous_summary}"""


async def summarize_messages(messages: list[dict], previous_summary: str = "") -> str:
    """Generate a rolling summary — integrates new messages with existing summary."""
    if not messages:
        return previous_summary

    formatted = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if content:
            formatted.append(f"{role}: {content[:500]}")

    conversation_text = "\n".join(formatted)

    llm = get_llm()
    prompt_text = SUMMARIZE_PROMPT.format(
        messages=conversation_text,
        previous_summary=previous_summary or "(none)",
    )
    prompt = [{"role": "user", "content": prompt_text}]

    try:
        response = await llm.ainvoke(prompt)
        summary = response.content.strip()
        logger.info(f"Generated summary: {len(summary)} chars from {len(messages)} messages")
        return summary
    except Exception as e:
        logger.warning(f"Summarization failed: {e}")
        return previous_summary


async def store_summary(
    store: AsyncPostgresStore,
    summary: str,
    business_id: str,
    thread_id: str,
) -> bool:
    """Store a summary in the long-term archive."""
    if not summary:
        return False

    namespace = (business_id, "summaries")
    key = str(uuid.uuid4())
    value = {
        "type": "summary",
        "content": summary,
        "thread_id": thread_id,
        "business_id": business_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        await store.aput(namespace, key, value)
        logger.info(f"Stored summary for {business_id}:{thread_id}")
        return True
    except Exception as e:
        logger.warning(f"Failed to store summary: {e}")
        return False


async def get_latest_summary(
    store: AsyncPostgresStore,
    business_id: str,
    limit: int = 3,
) -> str:
    """Retrieve the most recent summaries for a business."""
    namespace = (business_id, "summaries")

    try:
        results = await store.asearch(namespace, query="conversation summary", limit=limit)
        if not results:
            return ""

        summaries = []
        for item in results:
            content = item.value.get("content", "")
            if content:
                summaries.append(content)

        if not summaries:
            return ""

        return "\n---\n".join(summaries)
    except Exception as e:
        logger.warning(f"Failed to retrieve summaries: {e}")
        return ""
