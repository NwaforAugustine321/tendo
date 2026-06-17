"""Response node — produces final output and persists conversation."""

from app.models.state import GraphState


def response_node(state: GraphState) -> dict:
    # TODO: format final response, persist to Mem0
    return {"response": {"mode": "conversation", "text": ""}}
