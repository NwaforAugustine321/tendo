"""Response node — produces final output."""

from app.models.state import GraphState


def response_node(state: GraphState) -> dict:
    # TODO: format final response, persist to memory
    return {"response": {"mode": "conversation", "text": ""}}
