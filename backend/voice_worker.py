"""LiveKit Voice Agent Worker — runs as a separate process.

Connects to LiveKit Cloud, auto-joins rooms when participants connect,
and handles the full STT → Planner → TTS pipeline.

Run with:
    python voice_worker.py dev      (development mode)
    python voice_worker.py start    (production mode)
    python voice_worker.py console  (talk directly in terminal)
"""

import json
import logging
import os
import sys
import textwrap

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("voice-worker")

# Ensure the app modules are importable
sys.path.insert(0, os.path.dirname(__file__))

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    RunContext,
    TurnHandlingOptions,
    cli,
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
                Speak the tool result back to the user naturally and concisely.
                If the tool fails, apologize briefly and ask them to try again.
            """),
        )
        self._business_id = business_id
        self._session_id = session_id
        self._user_id = user_id
        self._graph_initialized = False

    async def _ensure_graph(self):
        if not self._graph_initialized:
            from app.graph.workflow import init_graph, get_graph
            try:
                get_graph()
            except RuntimeError:
                await init_graph()
            self._graph_initialized = True

    @function_tool
    async def process_request(self, context: RunContext, user_message: str):
        """Forward the user's request to the Tendo backend planner.

        Args:
            user_message: What the user said.
        """
        logger.info(f"[process_request] user={self._user_id} biz={self._business_id} session={self._session_id} msg={user_message[:80]}")

        await self._ensure_graph()

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
            logger.info(f"[process_request] response={response_text[:80]}")
            return response_text or "Done."
        except Exception as e:
            logger.error(f"[process_request] failed: {e}", exc_info=True)
            return "Something went wrong processing your request."


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

    # Fallback: extract business_id from room name (tendo-{business_id})
    if not business_id and ctx.room.name and ctx.room.name.startswith("tendo-"):
        business_id = ctx.room.name[len("tendo-"):]

    user_id = meta.get("user_id", "")

    if not business_id:
        logger.error("[tendo_session] No business_id in room metadata — cannot proceed")
        return

    if not user_id:
        logger.warning("[tendo_session] No user_id in room metadata — using 'anonymous'")
        user_id = "anonymous"

    logger.info(f"[tendo_session] business_id={business_id} session_id={session_id}")

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
    logger.info(f"[tendo_session] Agent connected and listening")


if __name__ == "__main__":
    cli.run_app(server)
