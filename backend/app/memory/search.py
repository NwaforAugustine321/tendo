"""Retrieve conversation memories from Mem0."""

from app.memory.client import get_client


def search(query: str, user_id: str) -> list[str]:
    """Search Mem0 for relevant memories."""
    client = get_client()
    results = client.search(query, user_id=user_id)
    return [r.get("memory", "") for r in results if r.get("memory")]
