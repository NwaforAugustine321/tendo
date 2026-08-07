"""LiveKit Voice Agent Worker — runs as a separate process.

Uses LangGraph LLMAdapter to route speech directly through the backend graph.
STT → LangGraph (your planner/agents) → TTS. No extra LLM hops.

Run with:
    python voice_worker.py dev
    python voice_worker.py start
"""

import json
import logging
import os
import sys
from typing import Annotated, TypedDict

from dotenv import load_dotenv

load_dotenv()

if os.getenv("NVIDIA_API_KEY") is None and os.getenv("nvidia_api_key"):
    os.environ["NVIDIA_API_KEY"] = os.getenv("nvidia_api_key", "")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("voice-worker")

sys.path.insert(0, os.path.dirname(__file__))

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.config import get_stream_writer
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages

from livekit.agents import (
    Agent,
    AgentSession,
    AgentServer,
    JobContext,
    TurnHandlingOptions,
    cli,
    inference,
)
from livekit.plugins import langchain, nvidia


class VoiceGraphState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    business_id: str
    session_id: str
    user_id: str


_graph_initialized = False


async def _ensure_graph():
    global _graph_initialized
    if not _graph_initialized:
        from app.graph.workflow import init_graph, get_graph
        try:
            get_graph()
        except RuntimeError:
            await init_graph()
        _graph_initialized = True


async def process_node(state: VoiceGraphState):
    writer = get_stream_writer()

    messages = state["messages"]
    business_id = state.get("business_id", "")
    session_id = state.get("session_id", "")
    user_id = state.get("user_id", "anonymous")

    last_human = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human = msg.content
            break

    if not last_human:
        response = "I didn't catch that. Could you repeat?"
        writer(response)
        return {"messages": [AIMessage(content=response)]}

    await _ensure_graph()

    from app.communication.voice import _run_graph

    try:
        result = await _run_graph(
            last_human,
            session_id,
            business_id,
            None,
            user_id,
        )
        response_text = result.get("text", "") or "Done."
    except Exception as e:
        logger.error(f"[process_node] failed: {e}", exc_info=True)
        response_text = "Something went wrong. Please try again."

    logger.info(f"[process_node] response: {response_text[:80]}")
    writer(response_text)
    return {"messages": [AIMessage(content=response_text)]}


def create_voice_graph():
    builder = StateGraph(VoiceGraphState)
    builder.add_node("process", process_node)
    builder.add_edge(START, "process")
    return builder.compile()


server = AgentServer()


@server.rtc_session(agent_name="tendo-voice")
async def tendo_session(ctx: JobContext):
    logger.info(f"[tendo_session] Room joined: {ctx.room.name}")

    metadata_str = ctx.room.metadata or "{}"
    try:
        meta = json.loads(metadata_str)
    except Exception:
        meta = {}

    business_id = meta.get("business_id", "")
    session_id = meta.get("session_id", "")

    if not business_id and ctx.room.name and ctx.room.name.startswith("tendo-"):
        business_id = ctx.room.name[len("tendo-"):]

    user_id = meta.get("user_id", "")

    if not business_id:
        logger.error("[tendo_session] No business_id in room metadata")
        return

    if not user_id:
        logger.warning("[tendo_session] No user_id — using 'anonymous'")
        user_id = "anonymous"

    logger.info(f"[tendo_session] business_id={business_id} session_id={session_id}")

    ctx.log_context_fields = {"room": ctx.room.name}

    graph = create_voice_graph()

    agent = Agent(
        instructions="",
        llm=langchain.LLMAdapter(
            graph=graph,
            stream_mode="custom",
            context={
                "business_id": business_id,
                "session_id": session_id,
                "user_id": user_id,
            },
        ),
    )

    session = AgentSession(
        stt=nvidia.STT(language_code="en-US"),
        tts=nvidia.TTS(
            voice="Magpie-Multilingual.EN-US.Leo",
            language_code="en-US",
        ),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
        ),
    )

    await session.start(agent=agent, room=ctx.room)
    await ctx.connect()
    logger.info(f"[tendo_session] Agent connected and listening")


if __name__ == "__main__":
    cli.run_app(server)
