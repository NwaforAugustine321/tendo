"""Conversation output formatting."""


def format_response(text: str) -> dict:
    """Format a conversation-mode response."""
    return {"mode": "conversation", "text": text[:2000]}
