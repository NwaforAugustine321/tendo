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

load_dotenv()

if os.getenv("NVIDIA_API_KEY") is None and os.getenv("nvidia_api_key"):
    os.environ["NVIDIA_API_KEY"] = os.getenv("nvidia_api_key", "")

logging.basicConfig(level=logging.INFO,
                    format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("voice-worker")
logging.getLogger("livekit.agents").setLevel(logging.WARNING)
logging.getLogger("livekit").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

sys.path.insert(0, os.path.dirname(__file__))

_warm_graph = None
_warm_stt = None
_warm_tts = None


def _get_warm_resources():
    global _warm_graph, _warm_stt, _warm_tts
    if _warm_graph is None:
        from app.graph.workflow import get_graph
        _warm_graph = get_graph()
    if _warm_stt is None:
        _warm_stt = nvidia.STT(language_code="en-US")
    if _warm_tts is None:
        _warm_tts = nvidia.TTS(
            voice="Magpie-Multilingual.EN-US.Jason",
            language_code="en-US",
        )
    return _warm_graph, _warm_stt, _warm_tts


server = AgentServer(num_idle_processes=2)


@server.rtc_session(agent_name="tendo-voice")
async def tendo_session(ctx: JobContext):
    graph, warm_stt, warm_tts = _get_warm_resources()

    metadata_str = ctx.job.metadata or ctx.room.metadata or "{}"
    try:
        meta = json.loads(metadata_str)
    except Exception:
        meta = {}

    business_id = meta.get("business_id", "")
    session_id = meta.get("session_id", "")
    record_id = meta.get("record_id", "")
    user_id = meta.get("user_id", "")

    if not business_id:
        logger.error("[tendo_session] No business id")
        await ctx.shutdown()
        return

    if not session_id:
        logger.error("[tendo_session] No session id")
        await ctx.shutdown()
        return

    if not user_id:
        logger.error("[tendo_session] No user id")
        await ctx.shutdown()
        return

    logger.info(
        f"[tendo_session] business_id={business_id} session_id={session_id}")
    ctx.log_context_fields = {"room": ctx.room.name}

    def _chunk_for_tts(text: str, max_len: int = 380) -> list[str]:
        """Split text into chunks ≤ max_len at sentence boundaries."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = ""
        for sentence in sentences:
            if len(sentence) > max_len:
                # Split long sentences at comma/semicolon boundaries
                parts = re.split(r'(?<=[,;])\s+', sentence)
                for part in parts:
                    if len(current) + len(part) + 1 > max_len:
                        if current:
                            chunks.append(current.strip())
                        # If single part exceeds max, hard-split at word boundary
                        while len(part) > max_len:
                            split_at = part.rfind(' ', 0, max_len)
                            if split_at == -1:
                                split_at = max_len
                            chunks.append(part[:split_at].strip())
                            part = part[split_at:].strip()
                        current = part
                    else:
                        current = f"{current} {part}" if current else part
            elif len(current) + len(sentence) + 1 > max_len:
                if current:
                    chunks.append(current.strip())
                current = sentence
            else:
                current = f"{current} {sentence}" if current else sentence
        if current:
            chunks.append(current.strip())
        return chunks

    session = AgentSession(
        stt=warm_stt,
        tts=warm_tts,
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
        "user_id": user_id,
    }

    agent = Agent(
        instructions="",
        llm=langchain.LLMAdapter(
            graph=graph,
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
        await session.aclose()

    ctx.add_shutdown_callback(_shutdown)


if __name__ == "__main__":
    cli.run_app(server)
