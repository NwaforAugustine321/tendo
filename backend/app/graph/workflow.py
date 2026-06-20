"""Workflow assembly — state graph with all nodes wired.

Graph is built once at startup and cached. Connection pools handle reconnection
at the driver level — no rebuild needed per request.
"""

import logging

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.bsga import bsga_node
from app.graph.nodes.db_translator import db_translator_node
from app.graph.nodes.db import db_node
from app.graph.nodes.domain_router import domain_router_node
from app.graph.nodes.moa import moa_node
from app.graph.nodes.response import response_node
from app.graph.nodes.tool_planner import tool_planner_node
from app.models.state import GraphState

logger = logging.getLogger(__name__)

_compiled_graph = None


def route_from_bsga(state: GraphState) -> str:
    if state.get("classification") == "OUT_OF_SCOPE":
        return "response"
    return "moa"


def route_from_moa(state: GraphState) -> str:
    if state.get("error"):
        return "response"

    tool_requests = state.get("tool_requests")
    if tool_requests:
        if isinstance(tool_requests, list) and len(tool_requests) > 0:
            if isinstance(tool_requests[0], dict) and "tool" in tool_requests[0]:
                return "db_oracle"
        return "tool_planner"

    routed = state.get("routed_domain")
    if routed:
        return "domain_router"

    return "response"


def build_graph() -> StateGraph:
    builder = StateGraph(GraphState)

    builder.add_node("bsga", bsga_node)
    builder.add_node("moa", moa_node)
    builder.add_node("tool_planner", tool_planner_node)
    builder.add_node("db_oracle", db_node)
    builder.add_node("db_translator", db_translator_node)
    builder.add_node("domain_router", domain_router_node)
    builder.add_node("response", response_node)

    builder.add_edge(START, "bsga")
    builder.add_conditional_edges("bsga", route_from_bsga, ["moa", "response"])

    builder.add_conditional_edges(
        "moa",
        route_from_moa,
        ["tool_planner", "db_oracle", "domain_router", "response"],
    )

    builder.add_edge("domain_router", "moa")
    builder.add_edge("tool_planner", "moa")

    builder.add_edge("db_oracle", "db_translator")
    builder.add_edge("db_translator", "moa")

    builder.add_edge("response", END)

    return builder


async def init_graph():
    """Initialize the graph once at app startup. Fails fast if connections fail."""
    global _compiled_graph

    from app.memory import ensure_checkpointer, ensure_store

    checkpointer = await ensure_checkpointer()
    store = await ensure_store()
    builder = build_graph()
    _compiled_graph = builder.compile(checkpointer=checkpointer, store=store)
    logger.info("Graph compiled and ready")
    return _compiled_graph


def get_graph():
    """Return the pre-compiled graph. Must call init_graph() first at startup."""
    if _compiled_graph is None:
        raise RuntimeError("Graph not initialized. Call init_graph() during app startup.")
    return _compiled_graph
