"""Reusable prompt trimming logic — trim messages and archive overflow."""

import asyncio
import logging

from app.config.settings import settings
from app.memory.long_term_mem import ensure_store
from app.memory.archiver import archive_messages
from app.memory.trimmer import count_tokens, trim_messages_to_limit

logger = logging.getLogger(__name__)


async def trim_and_archive(
    prompt: list[dict],
    business_id: str,
    thread_id: str,
    token_limit: int | None = None,
) -> list[dict]:
    """
    Trim prompt messages if over token limit. Archive trimmed messages to long-term store.
    Returns the (possibly trimmed) prompt. Never blocks — fails gracefully.
    Never trims if fewer than 6 messages (system + minimal context).
    """
    limit = token_limit or settings.max_message_token_size

    # Don't trim short conversations — keep at least 6 messages
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
        archived = await archive_messages(
            store=store,
            messages=trim_result.trimmed_messages,
            business_id=business_id,
            thread_id=thread_id,
        )
        if archived:
            logger.info(
                "Trimmed %d messages for %s:%s",
                len(trim_result.trimmed_messages),
                business_id,
                thread_id,
            )
            return trim_result.retained_messages
    except Exception as e:
        logger.warning("Archival failed for %s:%s: %s", business_id, thread_id, e)

    return prompt
