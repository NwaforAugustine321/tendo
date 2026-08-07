"""LiveKit Agent provider — full voice pipeline using LiveKit Agents SDK.

Runs a LiveKit Agent Server that joins rooms when participants connect.
Uses AgentSession with STT, TTS, Turn Detection, and Preemptive generation.

When the user speaks, STT transcribes it. The transcribed text is routed
to the backend planner/sub-agents via a function tool. The planner response
is then spoken back via TTS.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import textwrap

logger = logging.getLogger(__name__)

_server = None
_started = False


# --- Module-level definitions (required for multiprocessing pickling) ---

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    RunContext,
    TurnHandlingOptions,
    function_tool,
    inference,
    room_io,
)


class TendoVoiceAgent(Agent):
    def __init__(self, business_id: str = "", session_id: str = "", user_id: str = "anonymous") -> None:
        super().__init__(
            llm=inference.LLM(model="google/gemma-4-31b-it"),
            instructions=textwrap.dedent("""\
                You are Tendo, a voice assistant for business owners.
                When the user speaks, use the process_request tool to handle their request.
                Speak the tool result back to the user naturally.
                If the tool fails, apologize briefly and ask the user to try again.
                Keep your own responses short — the tool provides the real answer.
            """),
        )
        self._business_id = business_id
        self._session_id = session_id
        self._user_id = user_id

    @function_tool
    async def process_request(self, context: RunContext, user_message: str):
        """Forward the user's request to the Tendo backend planner for processing.

        Args:
            user_message: The transcribed text from the user's speech.
        """
        from app.communication.voice import _run_graph

        try:
            result = await _run_graph(
                user_message,
                self._session_id,
                self._business_id,
                None,
                self._user_id,
            )
            response_text = result.get("text", "")
            return response_text or "I processed your request but got no response."
        except Exception as e:
            logger.error(f"Planner call failed: {e}")
            return "Something went wrong processing your request."


async def tendo_session(ctx: JobContext):
    metadata_str = ctx.room.metadata or "{}"
    try:
        meta = json.loads(metadata_str)
    except Exception:
        meta = {}

    business_id = meta.get("business_id", "")
    session_id = meta.get("session_id", "")
    user_id = meta.get("user_id", "")

    if not business_id or not user_id:
        logger.error(f"[tendo_session] Missing required metadata: business_id={business_id} user_id={user_id}")
        return

    ctx.log_context_fields = {"room": ctx.room.name}

    session = AgentSession(
        stt=inference.STT(model="deepgram/nova-3", language="multi"),
        tts=inference.TTS(
            model="cartesia/sonic-3",
            voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        ),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
        ),
    )

    await session.start(
        agent=TendoVoiceAgent(
            business_id=business_id,
            session_id=session_id,
            user_id=user_id,
        ),
        room=ctx.room,
    )

    await ctx.connect()


# --- Server management ---

def get_agent_server():
    global _server

    if _server is not None:
        return _server

    _server = AgentServer()
    _server.rtc_session(agent_name="tendo-voice")(tendo_session)

    return _server


async def start_agent_worker():
    global _started

    if _started:
        return

    from app.config.settings import settings

    if not settings.livekit_url or not settings.livekit_api_key or not settings.livekit_api_secret:
        logger.warning("LiveKit credentials not configured — voice agent disabled")
        return

    os.environ.setdefault("LIVEKIT_URL", settings.livekit_url)
    os.environ.setdefault("LIVEKIT_API_KEY", settings.livekit_api_key)
    os.environ.setdefault("LIVEKIT_API_SECRET", settings.livekit_api_secret)

    _started = True
    server = get_agent_server()
    logger.info("LiveKit agent worker starting...")

    asyncio.create_task(_run_server(server))


async def _run_server(server):
    try:
        await server.run()
    except Exception as e:
        logger.error(f"LiveKit agent server error: {e}", exc_info=True)
