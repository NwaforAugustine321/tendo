"""DB node — executes tool requests."""

from app.models.state import GraphState


def db_node(state: GraphState) -> dict:
    # TODO: execute tool_requests via registry
    return {"db_result": {}}
