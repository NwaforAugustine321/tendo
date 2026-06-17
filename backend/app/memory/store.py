"""Persist conversation turns to memory."""

from app.memory.client import get_client


def store_turn(user_id: str, user_text: str, assistant_text: str) -> None:
    """Store a conversation turn for long-term recall."""
    get_client().add(
        [
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ],
        user_id=user_id,
        metadata={"source": "tendo", "type": "business_conversation"},
    )
