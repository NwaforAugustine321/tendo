"""Memory node — retrieves conversation context from Mem0."""

from app.models.state import GraphState


def memory_node(state: GraphState) -> dict:
    # TODO: retrieve from Mem0
    return {"messages": state.get("messages", [])}
