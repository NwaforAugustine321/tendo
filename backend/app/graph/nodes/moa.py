"""MOA (Tendo) graph node — master orchestrator."""

from app.models.state import GraphState


def moa_node(state: GraphState) -> dict:
    # TODO: load cache, decide sufficiency, route
    return {}
