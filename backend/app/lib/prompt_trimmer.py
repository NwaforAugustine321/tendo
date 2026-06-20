"""Reusable prompt trimming logic — summarize + archive overflow."""

import asyncio
import logging

from app.config.settings import settings
from app.memory.long_term_mem import ensure_store
from app.memory.archiver import archive_messages
from app.memory.summarizer import summarize_messages, store_summary
from app.memory.trimmer import count_tokens, trim_messages_to_limit

logger = logging.getLogger(__name__)


async def trim_and_archive(
    prompt: list[dict],
    business_id: str,
    thread_id: str,
    token_limit: int | None = None,
) -> list[dict]:
    """
    Trim prompt messages if over token limit.
    1. Summarize the trimmed messages
    2. Archive raw messages + store summary
    3. Return trimmed prompt

    Never blocks — fails gracefully.
    Never trims if fewer than 6 messages.
    """
    limit = token_limit or settings.max_message_token_size

    if len(prompt) <= 6:
        return prompt

    token_count = await asyncio.to_thread(count_tokens, prompt)
    if token_count <= limit:
        return prompt

    trim_result = await asyncio.to_thread(trim_messages_to_limit, prompt, limit)
    if not trim_result.trimmed_messages:
        return prompt

    try:
        store = await ensure_store()

        # Get existing summary to build on (rolling summary)
        from app.memory.summarizer import get_latest_summary
        previous_summary = await get_latest_summary(store, business_id, limit=1)

        # Summarize + archive in parallel
        summary_task = summarize_messages(trim_result.trimmed_messages, previous_summary)
        archive_task = archive_messages(
            store=store,
            messages=trim_result.trimmed_messages,
            business_id=business_id,
            thread_id=thread_id,
        )

        summary, archived = await asyncio.gather(summary_task, archive_task)

        # Store the new rolling summary
        if summary:
            await store_summary(store, summary, business_id, thread_id)

        if archived:
            logger.info(
                "Trimmed %d messages (summarized + archived) for %s:%s",
                len(trim_result.trimmed_messages),
                business_id,
                thread_id,
            )
            return trim_result.retained_messages

    except Exception as e:
        logger.warning("Trim+archive failed for %s:%s: %s", business_id, thread_id, e)

    return prompt
