import logging
from langgraph.graph import END, START, StateGraph
from app.graph.nodes.moa_orchestrator import moa_orchestrator_node
from app.graph.nodes.response import response_node
from app.models.state import GraphState

logger = logging.getLogger(__name__)

_compiled_graph = None


def route_from_moa(state: GraphState) -> str:
    if state.get("error"):
        return "response"
    return "response"


def build_graph() -> StateGraph:
    builder = StateGraph(GraphState)

    builder.add_node("moa", moa_orchestrator_node)
    builder.add_node("response", response_node)

    builder.add_edge(START, "moa")
    builder.add_edge("moa", "response")
    builder.add_edge("response", END)

    return builder


async def init_graph():
    global _compiled_graph
    builder = build_graph()
    _compiled_graph = builder.compile()
    logger.info("Graph compiled — MOA Orchestrator architecture")
    return _compiled_graph


def get_graph():
    if _compiled_graph is None:
        raise RuntimeError("Graph not initialized. Call init_graph() during app startup.")
    return _compiled_graph
