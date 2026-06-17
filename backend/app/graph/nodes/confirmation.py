"""Confirmation Gate node — presents write operation for user approval."""

from app.models.state import GraphState


def confirmation_node(state: GraphState) -> dict:
    # TODO: present confirmation card, wait for user response
    return {"confirmation_status": "pending"}
