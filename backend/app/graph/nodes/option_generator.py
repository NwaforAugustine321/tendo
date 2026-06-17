"""Option Generator node — produces structured option cards."""

from app.models.state import GraphState


def option_generator_node(state: GraphState) -> dict:
    # TODO: generate STRUCTURED_OPTIONS output
    return {"output_mode": "structured_options"}
