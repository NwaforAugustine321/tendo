import json
import logging
import os
import sys
from dotenv import load_dotenv
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
from livekit.agents import ErrorEvent, llm, stt, tts
import asyncio

load_dotenv()

if os.getenv("NVIDIA_API_KEY") is None and os.getenv("nvidia_api_key"):
    os.environ["NVIDIA_API_KEY"] = os.getenv("nvidia_api_key", "")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("voice-worker")

sys.path.insert(0, os.path.dirname(__file__))

server = AgentServer()


@server.rtc_session(agent_name="tendo-voice")
async def tendo_session(ctx: JobContext):

    from app.graph.workflow import get_graph

    metadata_str = ctx.job.metadata or ctx.room.metadata or "{}"
    try:
        meta = json.loads(metadata_str)
    except Exception:
        meta = {}

    business_id = meta.get("business_id", "")
    session_id = meta.get("session_id", "")
    record_id = meta.get("record_id", "")
    thread_id = meta.get("thread_id", "")
    user_id = meta.get("user_id", "")

    if not business_id:
        logger.error("[tendo_session] No business id ")
        payload = {"type": "error", "data": "Unauthorized, no business id"}
        data = json.dumps(payload).encode("utf-8")
        await ctx.room.local_participant.publish_data(data, reliable=True)
        return

    if not session_id:
        logger.error("[tendo_session] No session id")
        payload = {"type": "error", "data": "Unauthorized, no session id"}
        data = json.dumps(payload).encode("utf-8")
        await ctx.room.local_participant.publish_data(data, reliable=True)
        return

    if not user_id:
        logger.error("[tendo_session] No user id")
        payload = {"type": "error", "data": "Unauthorized, no user id"}
        data = json.dumps(payload).encode("utf-8")
        await ctx.room.local_participant.publish_data(data, reliable=True)
        return

    logger.info(f"[tendo_session] business_id={business_id} session_id={session_id}")
    ctx.log_context_fields = {"room": ctx.room.name}

    session = AgentSession(
        stt=nvidia.STT(language_code="en-US"),
        tts=nvidia.TTS(
            voice="Magpie-Multilingual.EN-US.Jason",
            language_code="en-US",
        ),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            interruption={
               "mode": "adaptive",
               "backchannel_boundary": (0.5, 2.0)
            },
            endpointing={
               "mode": "dynamic"
           },
        ),
    )

    async def _voice_emit(event_name: str, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        await ctx.room.local_participant.publish_data(data, reliable=True)

    context = {
        "vc_session": session,
        "record_id": record_id,
        "business_id": business_id,
        "session_id": session_id,
        "emit_event": _voice_emit,
        "user_id": user_id,
    }

    agent = Agent(
        instructions="",
        llm=langchain.LLMAdapter(
            graph=get_graph(),
            stream_mode="custom",
            context=context,
            config={"configurable": {"thread_id": session_id}}
        ),
    )

    await session.start(
        agent=agent,
        room=ctx.room,
    )

    @session.on("error")
    def on_error(ev: ErrorEvent):
        if ev.error.recoverable:
            return
        if isinstance(ev.source, (tts.TTS, llm.LLM)):
            ev.error.recoverable = True
            return
        if isinstance(ev.source, stt.STT):
            session.update_agent(session.current_agent)
            ev.error.recoverable = True
            return

    await ctx.connect()

    @session.on("close")
    def on_close(*args):
        logger.info("[tendo_session] Session closed")

    async def _shutdown():
        logger.info("[tendo_session] Shutting down...")
        await session.aclose()
        logger.info("[tendo_session] Shutdown complete")

    ctx.add_shutdown_callback(_shutdown)


if __name__ == "__main__":
    cli.run_app(server)
