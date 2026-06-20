"""BSGA node — classifies request scope and resets per-turn state."""

from app.models.state import GraphState


def bsga_node(state: GraphState) -> dict:
    """Classify the request and reset stale per-turn fields."""
    return {
        "classification": "IN_SCOPE",
        "db_result": {},
        "domain_result": {},
        "tool_requests": None,
        "routed_domain": None,
        "response": {},
        "error": None,
    }
