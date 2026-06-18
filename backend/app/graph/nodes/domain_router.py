"""Domain Router node — routes to the correct domain agent."""

from app.models.state import GraphState


def domain_router_node(state: GraphState) -> dict:
    return {"domain_result": {}}
