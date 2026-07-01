"""Workflow assembly — call-stack architecture where specialists own their workflows.

MOA runs once. Specialists own their tool loops. db_translator returns dynamically
to whoever requested the data via `return_to`.
"""

import logging

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.db_translator import db_translator_node
from app.graph.nodes.db import db_node
from app.graph.nodes.domain_router import domain_router_node
from app.graph.nodes.inventory import inventory_node
from app.graph.nodes.moa import moa_node
from app.graph.nodes.onboarding import onboarding_node
from app.graph.nodes.response import response_node
from app.graph.nodes.tool_planner import tool_planner_node
from app.graph.nodes.transactions import transactions_node
from app.models.state import GraphState

logger = logging.getLogger(__name__)

_compiled_graph = None


# --- Routing functions ---


def route_from_moa(state: GraphState) -> str:
    """MOA only runs once — either answers directly, routes to specialist, or needs its own tools."""
    if state.get("error"):
        return "response"

    if state.get("routed_domain"):
        return "domain_router"

    if state.get("tool_requests"):
        return "tool_planner"

    return "response"


def route_from_domain_router(state: GraphState) -> str:
    """Dispatch to the correct specialist node."""
    owner = state.get("workflow_owner") or ""
    if owner in ("onboarding", "transactions", "inventory"):
        return owner
    return "response"


def route_from_specialist(state: GraphState) -> str:
    """Specialist either finishes (→ response) or needs DB data (→ tool_planner)."""
    if state.get("tool_requests"):
        return "tool_planner"
    return "response"


def route_from_db_translator(state: GraphState) -> str:
    """Dynamic return — go back to whoever requested the data."""
    return_to = state.get("return_to") or "response"
    if return_to in ("moa", "onboarding", "transactions", "inventory"):
        return return_to
    return "response"


# --- Graph construction ---


def build_graph() -> StateGraph:
    builder = StateGraph(GraphState)

    # Nodes
    builder.add_node("moa", moa_node)
    builder.add_node("domain_router", domain_router_node)
    builder.add_node("onboarding", onboarding_node)
    builder.add_node("transactions", transactions_node)
    builder.add_node("inventory", inventory_node)
    builder.add_node("tool_planner", tool_planner_node)
    builder.add_node("db_oracle", db_node)
    builder.add_node("db_translator", db_translator_node)
    builder.add_node("response", response_node)

    # Edges — start directly at MOA
    builder.add_edge(START, "moa")

    builder.add_conditional_edges(
        "moa",
        route_from_moa,
        ["domain_router", "tool_planner", "response"],
    )

    # Domain router dispatches to specialists
    builder.add_conditional_edges(
        "domain_router",
        route_from_domain_router,
        ["onboarding", "transactions", "inventory", "response"],
    )

    # Specialists either finish or need tools
    builder.add_conditional_edges(
        "onboarding",
        route_from_specialist,
        ["tool_planner", "response"],
    )
    builder.add_conditional_edges(
        "transactions",
        route_from_specialist,
        ["tool_planner", "response"],
    )
    builder.add_conditional_edges(
        "inventory",
        route_from_specialist,
        ["tool_planner", "response"],
    )

    # Tool execution chain
    builder.add_edge("tool_planner", "db_oracle")
    builder.add_edge("db_oracle", "db_translator")

    # DB translator returns to caller dynamically
    builder.add_conditional_edges(
        "db_translator",
        route_from_db_translator,
        ["moa", "onboarding", "transactions", "inventory", "response"],
    )

    builder.add_edge("response", END)

    return builder


async def init_graph():
    """Initialize the graph once at app startup. Fails fast if connections fail."""
    global _compiled_graph

    builder = build_graph()
    _compiled_graph = builder.compile()
    logger.info("Graph compiled and ready (no checkpointer — LanceDB handles memory)")
    return _compiled_graph


def get_graph():
    """Return the pre-compiled graph. Must call init_graph() first at startup."""
    if _compiled_graph is None:
        raise RuntimeError("Graph not initialized. Call init_graph() during app startup.")
    return _compiled_graph
