"""LiveKit Voice Worker — streams LLM tokens directly to TTS via LangGraph."""

import json
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

if os.getenv("NVIDIA_API_KEY") is None and os.getenv("nvidia_api_key"):
    os.environ["NVIDIA_API_KEY"] = os.getenv("nvidia_api_key", "")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("voice-worker")

sys.path.insert(0, os.path.dirname(__file__))

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

    from app.graph.voice_graph import get_voice_graph
    graph = get_voice_graph()

    agent = Agent(
        instructions="",
        llm=langchain.LLMAdapter(
            graph=graph,
            stream_mode="custom",
        ),
    )

    session = AgentSession(
        stt=nvidia.STT(language_code="en-US"),
        tts=nvidia.TTS(
            voice="Magpie-Multilingual.EN-US.Jason",
            language_code="en-US",
        ),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
        ),
    )

    await session.start(
        agent=agent,
        room=ctx.room,
    )

    from app.planner.planner import set_active_session
    set_active_session(session, business_id)

    from livekit.agents import ErrorEvent, llm, stt, tts

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
    logger.info(f"[tendo_session] Agent connected and listening")

    @session.on("close")
    def on_close(*args):
        logger.info("[tendo_session] Session closed, shutting down")

    async def _shutdown():
        await session.aclose()

    ctx.add_shutdown_callback(_shutdown)


if __name__ == "__main__":
    cli.run_app(server)
