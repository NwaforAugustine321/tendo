"""BSGA node — classifies request scope."""

from app.models.state import GraphState


def bsga_node(state: GraphState) -> dict:
    return {"classification": "IN_SCOPE"}
