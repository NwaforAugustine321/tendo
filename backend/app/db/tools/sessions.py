"""Conversation session tools."""

from app.db.registry import register


@register("create_session")
def create_session(business_id: str, user_id: str, title: str) -> dict:
    """Create a new conversation session."""
    # TODO: implement via app.db.client
    return {"status": "created", "title": title}


@register("get_session_messages")
def get_session_messages(business_id: str, session_id: str) -> dict:
    """Get messages for a conversation session."""
    # TODO: implement
    return {"messages": []}


@register("store_message")
def store_message(
    business_id: str,
    session_id: str,
    role: str,
    content: str,
    message_type: str = "text",
    metadata: dict | None = None,
) -> dict:
    """Store a message in a conversation session."""
    # TODO: implement
    return {"status": "stored"}
