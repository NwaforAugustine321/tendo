"""Confirmation node — presents write operations for user approval."""

from app.models.state import GraphState


def confirmation_node(state: GraphState) -> dict:
    return {"confirmation_status": "pending"}
