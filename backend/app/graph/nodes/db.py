"""DB Oracle node — executes tool requests via Supabase."""

from app.models.state import GraphState


def db_node(state: GraphState) -> dict:
    # TODO: execute tool_requests via db/registry
    return {"db_result": {}}
