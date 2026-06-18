"""Persist conversation turns to memory."""

import logging
from app.memory.client import get_client

logger = logging.getLogger(__name__)


def store_turn(user_id: str, user_text: str, assistant_text: str, metadata: dict | None = None) -> None:
    """Store a single conversation turn."""
    meta = {"source": "tendo", "type": "conversation"}
    if metadata:
        meta.update(metadata)

    try:
        get_client().add(
            [
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": assistant_text},
            ],
            user_id=user_id,
            metadata=meta,
        )
    except Exception as e:
        logger.warning(f"Failed to store turn in mem0: {e}")


def store_messages(user_id: str, messages: list[dict], metadata: dict | None = None) -> None:
    """Store a batch of messages."""
    meta = {"source": "tendo", "type": "conversation"}
    if metadata:
        meta.update(metadata)

    try:
        get_client().add(messages, user_id=user_id, metadata=meta)
    except Exception as e:
        logger.warning(f"Failed to store messages in mem0: {e}")
