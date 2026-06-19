"""Voice module — real-time streaming and one-shot voice operations."""

import asyncio
import logging
import re

from fastapi import WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

from app.ws.connection import accept, close
from app.ws.sender import send_audio, send_message, send_turn_complete, send_error, send_thinking
from app.ws.receiver import receive_json
from app.ws.encoding import decode_audio
from app.config.settings import settings

logger = logging.getLogger(__name__)


def _get_client():
    return genai.Client(api_key=settings.google_voice_api_key)


def _get_config() -> types.LiveConnectConfig:
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        output_audio_transcription=types.AudioTranscriptionConfig(),
        system_instruction=types.Content(
            parts=[types.Part.from_text(text="Repeat exactly what the user says. Do not add anything.")]
        ),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Charon")
            )
        ),
    )


def _clean_text(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[-*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text.strip()


async def _run_graph(user_text: str, thread_id: str, business_id: str, websocket=None, user_id: str = "anonymous") -> dict:
    from app.graph.workflow import get_graph
    from langgraph.types import Command

    graph = await get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    # Node-level thinking messages for the user
    NODE_THINKING = {
        "bsga": "Understanding your request...",
    }
    DEFAULT_THINKING = "Thinking..."

    async def _stream_invoke(input_data):
        """Stream graph execution and send thinking updates."""
        result = {}
        async for event in graph.astream(input_data, config=config, stream_mode="updates"):
            for node_name, node_output in event.items():
                # Send thinking message for this node
                if websocket and node_name != "response":
                    try:
                        msg = NODE_THINKING.get(node_name, DEFAULT_THINKING)
                        await send_thinking(websocket, msg)
                    except Exception:
                        pass
                # Keep the last output as the result
                if isinstance(node_output, dict):
                    result.update(node_output)
        return result

    # Check if the graph is interrupted (waiting for user input)
    state = await graph.aget_state(config)

    if state.tasks:
        # Graph is paused at an interrupt — resume with user's answer
        logger.info(f"Resuming interrupted graph with: {user_text[:50]}")
        try:
            result = await _stream_invoke(Command(resume=user_text))
        except TypeError:
            # Stale checkpoint with incompatible node signatures — start fresh
            logger.warning("Stale checkpoint detected, starting fresh invocation")
            input_state = {
                "event": {"text": user_text, "thread_id": thread_id, "business_id": business_id},
                "thread_id": thread_id,
                "business_id": business_id,
                "user_id": user_id,
            }
            result = await _stream_invoke(input_state)
    else:
        # Fresh invocation
        input_state = {
            "event": {"text": user_text, "thread_id": thread_id, "business_id": business_id},
            "thread_id": thread_id,
            "business_id": business_id,
            "user_id": user_id,
        }
        result = await _stream_invoke(input_state)

    response = result.get("response") or {}
    response["text"] = _clean_text(response.get("text", ""))

    # Check if graph is now interrupted (needs user input)
    new_state = await graph.aget_state(config)
    if new_state.tasks:
        # Graph paused — extract the interrupt value (the actual question to show)
        for task in new_state.tasks:
            if hasattr(task, 'interrupts') and task.interrupts:
                for intr in task.interrupts:
                    interrupt_data = intr.value if hasattr(intr, 'value') else intr
                    if isinstance(interrupt_data, dict):
                        # Use interrupt text as the response (this is the current step's text)
                        if interrupt_data.get("text"):
                            response["text"] = _clean_text(interrupt_data["text"])
                        if interrupt_data.get("questions"):
                            response["input"] = interrupt_data["questions"]
                        if interrupt_data.get("extracted"):
                            response["extracted"] = interrupt_data["extracted"]
                        break

    return response


async def _send_text_for_tts(session, text: str) -> bool:
    """Send text to Gemini Live for TTS playback. Returns False if session is dead."""
    try:
        await session.send_client_content(
            turns=[types.Content(role="user", parts=[types.Part.from_text(text=text)])],
            turn_complete=True,
        )
        return True
    except Exception as e:
        logger.warning(f"TTS send failed: {e}")
        return False


async def _send_audio_for_transcription(session, audio_data: bytes):
    """Send audio to Gemini Live for transcription."""
    await session.send_client_content(
        turns=[
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        inline_data=types.Blob(data=audio_data, mime_type="audio/pcm")
                    )
                ],
            )
        ],
        turn_complete=True,
    )


async def _stream_tts_response(session, websocket: WebSocket):
    """Read TTS audio from Gemini and stream to browser."""
    async for response in session.receive():
        if response.data:
            await send_audio(websocket, response.data)

        if response.server_content and response.server_content.turn_complete:
            await send_turn_complete(websocket)
            break


async def handle_session(websocket: WebSocket):
    await accept(websocket)
    logger.info("Voice WebSocket accepted")

    # Authenticate via cookie
    from app.services.auth import handle_get_me, COOKIE_NAME
    token = websocket.cookies.get(COOKIE_NAME)
    user = None
    user_id = None
    if token:
        user = await handle_get_me(token)
        if user:
            user_id = user["user_id"]
            logger.info(f"WebSocket authenticated: user_id={user_id}")
        else:
            logger.warning("WebSocket: invalid session token")
    else:
        logger.warning("WebSocket: no auth cookie, proceeding as anonymous")

    client = _get_client()
    config = _get_config()
    logger.info(f"Connecting to model: {settings.google_voice_model}")

    thread_id = websocket.query_params.get("session_id", "default")
    business_id = websocket.query_params.get("business_id", "default")

    try:
        async with client.aio.live.connect(
            model=settings.google_voice_model, config=config
        ) as session:
            logger.info("AI session connected")

            result = await _run_graph("hello", thread_id, business_id, websocket, user_id)
            greeting = result.get("text", "")

            if greeting:
                logger.info(f"Initial: {greeting[:80]}")
                await send_message(websocket, greeting, result.get("input"), result.get("extracted"))

                if await _send_text_for_tts(session, greeting):
                    async for response in session.receive():
                        if response.data:
                            await send_audio(websocket, response.data)
                        if response.server_content and response.server_content.turn_complete:
                            await send_turn_complete(websocket)
                            break
                else:
                    await send_turn_complete(websocket)

            while True:
                input_result = await _collect_input(websocket)
                if input_result is None:
                    break

                input_type, data = input_result
                user_text = ""

                if input_type == "text":
                    user_text = data
                    logger.info(f"Text input: {user_text[:50]}")

                elif input_type == "context":
                    # Wake word context frame — process intent without TTS response
                    context_data = data if isinstance(data, dict) else {}
                    intent = context_data.get("intent", "")
                    wake_phrase = context_data.get("wake_phrase", "")
                    logger.info(f"Context frame: wake={wake_phrase}, intent={intent[:50]}")
                    if intent:
                        user_text = intent
                    else:
                        continue

                    # Detect logo upload — extract data URL and store separately
                    if user_text.startswith("[LOGO_DATA]:"):
                        logo_data_url = user_text[len("[LOGO_DATA]:"):]
                        # Store in a variable accessible to _run_graph
                        self_logo_data = logo_data_url
                        user_text = "label: Business Logo, answer: [LOGO_UPLOADED], description: User uploaded a business profile image"
                        logger.info(f"Logo data received: {len(logo_data_url)} chars")
                    else:
                        self_logo_data = None

                elif input_type == "audio":
                    logger.info(f"Transcribing audio: {len(data)} bytes")
                    await _send_audio_for_transcription(session, data)

                    transcription_parts = []
                    async for response in session.receive():
                        if (
                            response.server_content
                            and response.server_content.output_transcription
                        ):
                            text = response.server_content.output_transcription.text
                            if text:
                                transcription_parts.append(text)
                        if response.server_content and response.server_content.turn_complete:
                            break

                    user_text = "".join(transcription_parts)
                    logger.info(f"Transcribed: {user_text[:80]}")

                if not user_text:
                    continue

                result = await _run_graph(user_text, thread_id, business_id, websocket, user_id)
                moa_response = result.get("text", "")
                logger.info(f"Response: {moa_response[:80]}")

                await send_message(websocket, moa_response, result.get("input"), result.get("extracted"))

                if await _send_text_for_tts(session, moa_response):
                    await _stream_tts_response(session, websocket)
                else:
                    await send_turn_complete(websocket)

                await asyncio.sleep(0.3)

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Session error: {e}", exc_info=True)
        await send_error(websocket, "Something went wrong. Please try again.")
    finally:
        await close(websocket)
        logger.info("WebSocket closed")


async def _collect_input(websocket: WebSocket) -> tuple[str, bytes | str | dict] | None:
    audio_buffer: list[bytes] = []

    while True:
        message = await receive_json(websocket)
        if message is None:
            return None

        kind = message.get("type")

        if kind == "audio":
            raw = decode_audio(message["data"])
            audio_buffer.append(raw)

        elif kind == "end_turn":
            if audio_buffer:
                full_audio = b"".join(audio_buffer)
                logger.info(f"Audio collected: {len(full_audio)} bytes from {len(audio_buffer)} chunks")
                return ("audio", full_audio)
            continue

        elif kind == "text":
            return ("text", message.get("data", ""))

        elif kind == "context":
            return ("context", message.get("data", {}))
