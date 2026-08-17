import logging
from typing import Annotated, TypedDict, Callable
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from app.planner import Planner
from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime
from langchain_core.runnables import RunnableConfig
from app.communication.ws.server import socket_dispatcher
from app.communication.events import ApplicationEvent
from app.communication.event_bus import get_event_bus
from app.communication.events import (
    EventDelivery,
)

logger = logging.getLogger(__name__)


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    business_id: str
    session_id: str
    user_id: str
    thread_id: str
    record_id: str


async def planner_node(state: State, config: RunnableConfig, runtime: Runtime):
    writer = get_stream_writer()
    context = runtime.context

    payload = context.get("payload", {})
    user_id = payload.get("user_id", "")

    session = {
        "vc_session": context['session'],
        "business_id":  payload.get("business_id", ""),
        "session_id":  payload.get("session_id", ""),
        "user_id":  payload.get("user_id", ""),
        "record_id":  payload.get("record_id", "")
    }

    planner = Planner(session=session)
    messages = state["messages"]

    user_message = ""
    for msg in messages:
        if isinstance(msg, HumanMessage):
            user_message = msg.content

    if not user_message:
        writer("I didn't catch that. Could you repeat?")
        return {"messages": []}

    if user_id and user_message:

        payload = {
            "type": "transcript",
            "payload": {
                "content": user_message,
            },
            "user_id": user_id,
            "event": "transcript",
        }

        await get_event_bus().publish(
            ApplicationEvent(
                event="transcript",
                source="app",
                delivery=EventDelivery.APP,
                data=payload,
            ),
        )

    response = await planner.run(user_message=user_message, messages=messages)
    writer(response or "")

    if user_id and response:
        await socket_dispatcher.emit_to_user(
            user_id=user_id,
            event="message",
            payload={
                "type": "message",
                "payload": {"content": user_message},
            },
        )

    return {"messages": []}


def build_graph() -> StateGraph:
    builder = StateGraph(State)
    builder.add_node("planner", planner_node)
    builder.add_edge(START, "planner")
    builder.add_edge("planner", END)
    return builder


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile()
    return _compiled_graph


graph = get_graph()
