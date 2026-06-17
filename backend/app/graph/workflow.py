"""Workflow assembly — state graph with all nodes wired."""

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.bsga import bsga_node
from app.graph.nodes.confirmation import confirmation_node
from app.graph.nodes.context_resolution import context_resolution_node
from app.graph.nodes.db import db_node
from app.graph.nodes.domain_router import domain_router_node
from app.graph.nodes.memory import memory_node
from app.graph.nodes.moa import moa_node
from app.graph.nodes.option_generator import option_generator_node
from app.graph.nodes.response import response_node
from app.graph.nodes.tool_planner import tool_planner_node
from app.models.state import GraphState


def route_from_bsga(state: GraphState) -> str:
    if state.get("classification") == "OUT_OF_SCOPE":
        return "response"
    return "memory"


def route_from_moa(state: GraphState) -> str:
    if state.get("error"):
        return "response"
    if state.get("output_mode") == "structured_options":
        return "option_generator"
    if state.get("tool_requests"):
        return "tool_planner"
    if state.get("routed_domain"):
        return "domain_router"
    if state.get("confirmation_status") == "pending":
        return "confirmation"
    return "response"


def build_graph() -> StateGraph:
    """Build the state graph with all nodes and edges."""
    builder = StateGraph(GraphState)

    builder.add_node("bsga", bsga_node)
    builder.add_node("memory", memory_node)
    builder.add_node("moa", moa_node)
    builder.add_node("tool_planner", tool_planner_node)
    builder.add_node("db_oracle", db_node)
    builder.add_node("context_resolution", context_resolution_node)
    builder.add_node("option_generator", option_generator_node)
    builder.add_node("domain_router", domain_router_node)
    builder.add_node("confirmation", confirmation_node)
    builder.add_node("response", response_node)

    builder.add_edge(START, "bsga")
    builder.add_conditional_edges("bsga", route_from_bsga, ["memory", "response"])
    builder.add_edge("memory", "moa")
    builder.add_conditional_edges(
        "moa",
        route_from_moa,
        ["tool_planner", "option_generator", "domain_router", "confirmation", "response"],
    )
    builder.add_edge("tool_planner", "db_oracle")
    builder.add_edge("db_oracle", "context_resolution")
    builder.add_edge("context_resolution", "moa")
    builder.add_edge("domain_router", "moa")
    builder.add_edge("option_generator", "response")
    builder.add_edge("confirmation", "moa")
    builder.add_edge("response", END)

    return builder


def compile_graph():
    """Compile the graph with checkpointer and interrupts."""
    from app.redis.checkpointer import get_checkpointer

    builder = build_graph()
    checkpointer = get_checkpointer()
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["confirmation", "option_generator"],
    )
