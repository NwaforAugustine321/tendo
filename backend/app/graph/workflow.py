import logging
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

logger = logging.getLogger(__name__)


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    business_id: str
    session_id: str
    user_id: str


_planner = None


def _get_planner():
    global _planner
    if _planner is None:
        from app.planner import Planner
        _planner = Planner()
    return _planner


async def planner_node(state: State):
    from langgraph.config import get_stream_writer
    writer = get_stream_writer()

    planner = _get_planner()
    messages = state["messages"]

    last_human = ""
    for msg in messages:
        if isinstance(msg, HumanMessage):
            last_human = msg.content

    if not last_human:
        writer("I didn't catch that. Could you repeat?")
        return {"messages": []}

    response_msg = await planner.run(user_request=last_human, messages=messages)
    writer(response_msg.content)
    return {"messages": []}


def build_graph() -> StateGraph:
    builder = StateGraph(State)
    builder.add_node("planner", planner_node)
    builder.add_edge(START, "planner")
    builder.add_edge("planner", END)
    return builder


_compiled_graph = None


async def init_graph():
    global _compiled_graph
    _compiled_graph = build_graph().compile()
    logger.info("Graph compiled")
    return _compiled_graph


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile()
    return _compiled_graph
