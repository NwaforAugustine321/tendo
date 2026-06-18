"""Retrieve conversation memories."""

import logging
from app.memory.client import get_client

logger = logging.getLogger(__name__)


def search(query: str, user_id: str, limit: int = 5) -> list[str]:
    """Search for relevant memories by semantic similarity."""
    try:
        client = get_client()
        results = client.search(query, filters={"user_id": user_id}, limit=limit)
        memories = []
        for r in results:
            if isinstance(r, str):
                memories.append(r)
            elif isinstance(r, dict) and r.get("memory"):
                memories.append(r["memory"])
        return memories
    except Exception as e:
        logger.warning(f"Memory search failed: {e}")
        return []


def get_history(user_id: str, limit: int = 10) -> list[dict]:
    """Get recent conversation history for a user."""
    try:
        client = get_client()
        results = client.get_all(filters={"user_id": user_id}, limit=limit)
        memories = []
        if isinstance(results, list):
            for r in results:
                if isinstance(r, str):
                    memories.append({"memory": r})
                elif isinstance(r, dict) and r.get("memory"):
                    memories.append({"memory": r["memory"], "created_at": r.get("created_at", "")})
        elif isinstance(results, dict):
            for r in results.get("results", []):
                if isinstance(r, str):
                    memories.append({"memory": r})
                elif isinstance(r, dict) and r.get("memory"):
                    memories.append({"memory": r["memory"], "created_at": r.get("created_at", "")})
        return memories
    except Exception as e:
        logger.warning(f"Failed to get history from mem0: {e}")
        return []
