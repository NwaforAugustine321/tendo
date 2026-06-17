"""BSGA graph node — classifies request scope."""

from app.models.state import GraphState


def bsga_node(state: GraphState) -> dict:
    # TODO: invoke BSGA agent for classification
    return {"classification": "IN_SCOPE"}
