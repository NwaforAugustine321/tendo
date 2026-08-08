import logging
from typing import Annotated, TypedDict, Callable
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from app.planner import Planner
from langgraph.config import get_config
from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime
from langchain_core.runnables import RunnableConfig


logger = logging.getLogger(__name__)



class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    business_id: str
    session_id: str
    user_id: str
    emit_event: Callable
    thread_id: str
    record_id: str


async def planner_node(state: State,config: RunnableConfig, runtime: Runtime):
    writer = get_stream_writer()
    # config = get_config()
    context = runtime.context

    session = {
       "vc_session": context['vc_session'],
       "business_id": context["business_id"],
       "emit_event": context["emit_event"],
       "session_id": context["session_id"],
       "user_id": context['user_id'],
       "record_id": context["record_id"]
    }

    emit_event = context.get("emit_event")
    planner =  Planner(session=session)
    messages = state["messages"]
    

    user_message = ""
    for msg in messages:
        if isinstance(msg, HumanMessage):
           user_message = msg.content

    if not user_message:
        writer("I didn't catch that. Could you repeat?")
        return {"messages": []}
        
    if emit_event and user_message:
        await emit_event("transcript", {
            "type": "transcript",
            "data": user_message,
        })
    response = await planner.run(user_message=user_message, messages=messages)
    writer(response  or "")
    if emit_event and response:
        await emit_event("message", {
            "type": "message",
            "data": {"response": response, "msg_type": "answer"},
        })
    return {"messages": []}


def build_graph() -> StateGraph:
    builder = StateGraph(State)
    builder.add_node("planner", planner_node)
    builder.add_edge(START, "planner")
    builder.add_edge("planner", END)
    return builder

graph = build_graph().compile()
