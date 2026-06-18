"""DB node — executes tool requests against the database."""

from app.models.state import GraphState


def db_node(state: GraphState) -> dict:
    return {"db_result": {}}
