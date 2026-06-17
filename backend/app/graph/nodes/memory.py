"""Memory node — retrieves conversation context."""

from app.models.state import GraphState


def memory_node(state: GraphState) -> dict:
    # TODO: retrieve from memory
    return {"messages": state.get("messages", [])}
