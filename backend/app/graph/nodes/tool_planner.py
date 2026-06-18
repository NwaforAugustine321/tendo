"""Tool Planner node — converts intent to structured tool call requests."""

from app.models.state import GraphState


def tool_planner_node(state: GraphState) -> dict:
    return {"tool_requests": []}
