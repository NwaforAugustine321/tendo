"""Domain Router node — routes to the correct domain agent."""

from app.models.state import GraphState


def domain_router_node(state: GraphState) -> dict:
    # TODO: invoke the appropriate domain agent (sales/payment/inventory/service)
    return {"domain_result": {}}
