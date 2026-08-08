"""Voice-optimized LangGraph — Planner runtime handles everything, streams to TTS."""

from __future__ import annotations

import logging
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

logger = logging.getLogger(__name__)


class VoiceState(TypedDict):
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


async def planner_node(state: VoiceState):
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


def build_voice_graph() -> StateGraph:
    builder = StateGraph(VoiceState)
    builder.add_node("planner", planner_node)
    builder.add_edge(START, "planner")
    builder.add_edge("planner", END)
    return builder


_compiled = None


def get_voice_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_voice_graph().compile()
    return _compiled
