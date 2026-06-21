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
from app.services.auth import handle_get_me, COOKIE_NAME

logger = logging.getLogger(__name__)

# Module-level singletons — created once at import time
_gemini_client = genai.Client(api_key=settings.google_voice_api_key)
_gemini_config = types.LiveConnectConfig(
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


async def _run_graph(user_text: str, thread_id: str, business_id: str, websocket=None, user_id: str = "anonymous", send_fn=None) -> dict:
    from app.graph.workflow import get_graph
    from langgraph.types import Command

    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 25}

    NODE_THINKING = {
        "bsga": "Understanding...",
        "moa": "Thinking...",
        "tool_planner": "Planning...",
        "db_oracle": "Fetching data...",
        "db_translator": "Processing results...",
        "domain_router": "Deciding...",
    }

    async def _send_thinking_msg(msg: str):
        if send_fn:
            try:
                await send_fn({"type": "thinking", "data": msg})
            except Exception:
                pass
        elif websocket:
            try:
                await send_thinking(websocket, msg)
            except Exception:
                pass

    async def _stream_invoke(input_data):
        """Stream graph execution and send thinking updates."""
        result = {}
        async for event in graph.astream(input_data, config=config, stream_mode="updates"):
            for node_name, node_output in event.items():
                if node_name != "response":
                    msg = NODE_THINKING.get(node_name, "Thinking...")
                    await _send_thinking_msg(msg)
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

        # If the resumed graph completed (no more interrupts), check if we should
        # also run a fresh invocation for the actual user question
        post_resume_state = await graph.aget_state(config)
        if not post_resume_state.tasks:
            # Graph finished after resume — the user's message was consumed as an interrupt answer
            # but they might be asking something new. Run fresh for the new message.
            response = result.get("response") or {}
            # Only re-run if the response looks like a completion/confirmation, not an answer to their question
            resp_text = response.get("text", "")
            if resp_text and user_text.lower() not in resp_text.lower() and not any(
                kw in user_text.lower() for kw in ["confirm", "yes", "save", "done", "ok", "cancel", "no"]
            ):
                logger.info("Post-resume: user asked a new question, running fresh graph")
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
    response["input"] = response.get("input")
    response["extracted"] = response.get("extracted")

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

    client = _gemini_client
    config = _gemini_config
    logger.info(f"Connecting to model: {settings.google_voice_model}")

    thread_id = websocket.query_params.get("session_id", "")
    business_id = websocket.query_params.get("business_id", "")

    try:
        async def _connect_gemini():
            return await client.aio.live.connect(
                model=settings.google_voice_model, config=config
            ).__aenter__()

        session = await _connect_gemini()
        logger.info("AI session connected")

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
        # Close Gemini session if it was opened
        try:
            await session.__aexit__(None, None, None)
        except Exception:
            pass
        await close(websocket)
        logger.info("WebSocket closed")


async def _collect_input(websocket: WebSocket) -> tuple[str, bytes | str] | None:
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


async def run_voice_session(
    session_id: str,
    business_id: str,
    user_id: str,
    receive,
    send,
):
    """Transport-agnostic voice session — used by Socket.IO handler.

    Args:
        session_id: Thread/session identifier for checkpoints.
        business_id: Business profile scope.
        user_id: Authenticated user ID.
        receive: Async callable that returns the next message dict (or None on disconnect).
        send: Async callable that sends a message dict to the client.
    """
    from app.ws.encoding import encode_audio, decode_audio

    thread_id = session_id
    client = _gemini_client
    config = _gemini_config

    async def _send_msg(msg_type: str, text: str = "", questions=None, extracted=None):
        msg = {"type": "message", "data": {"response": text, "msg_type": "answer"}}
        if questions:
            msg["data"]["msg_type"] = "question"
            msg["data"]["questions"] = questions
        if extracted:
            msg["data"]["extracted"] = extracted
        await send(msg)

    try:
        async def _connect_gemini():
            return await client.aio.live.connect(
                model=settings.google_voice_model, config=config
            ).__aenter__()

        import asyncio
        session = await _connect_gemini()
        logger.info("Socket.IO: Gemini session ready")

        await send({"type": "turn_complete"})

        while True:
            message = await receive()
            if message is None:
                break

            kind = message.get("type")

            if kind == "text":
                user_text = message.get("data", "")
                logger.info(f"Socket.IO text: {user_text[:50]}")

                result = await _run_graph(user_text, thread_id, business_id, None, user_id, send_fn=send)
                moa_response = result.get("text", "")
                logger.info(f"Socket.IO response: {moa_response[:80]}")

                await _send_msg("message", moa_response, result.get("input"), result.get("extracted"))

                # TTS is optional — skip if Gemini session is dead
                if session and moa_response:
                    try:
                        await session.send_client_content(
                            turns=[types.Content(role="user", parts=[types.Part.from_text(text=moa_response)])],
                            turn_complete=True,
                        )
                        async for response in session.receive():
                            if response.data:
                                await send({"type": "audio", "data": encode_audio(response.data)})
                            if response.server_content and response.server_content.turn_complete:
                                await send({"type": "turn_complete"})
                                break
                    except Exception as e:
                        logger.warning(f"Socket.IO TTS failed: {e}")
                        await send({"type": "turn_complete"})
                        try:
                            await session.__aexit__(None, None, None)
                        except Exception:
                            pass
                        session = None
                elif not session and moa_response:
                    # Try to reconnect Gemini for TTS
                    await send({"type": "turn_complete"})
                    try:
                        session = await client.aio.live.connect(
                            model=settings.google_voice_model, config=config
                        ).__aenter__()
                        logger.info("Socket.IO: Gemini session reconnected on text")
                    except Exception:
                        pass
                else:
                    await send({"type": "turn_complete"})

                await asyncio.sleep(0.3)

                try:
                    await session.send_client_content(
                        turns=[types.Content(role="user", parts=[types.Part.from_text(text=moa_response)])],
                        turn_complete=True,
                    )
                    async for response in session.receive():
                        if response.data:
                            await send({"type": "audio", "data": encode_audio(response.data)})
                        if response.server_content and response.server_content.turn_complete:
                            await send({"type": "turn_complete"})
                            break
                except Exception as e:
                    logger.warning(f"Socket.IO TTS failed: {e}")
                    await send({"type": "turn_complete"})
                    # Mark session as dead, will try to reconnect on next message
                    try:
                        await session.__aexit__(None, None, None)
                    except Exception:
                        pass
                    session = None

                await asyncio.sleep(0.3)

            elif kind == "audio":
                # If Gemini session is dead, skip audio silently
                if session is None:
                    continue

                audio_data = decode_audio(message.get("data", ""))
                try:
                    await session.send_client_content(
                        turns=[types.Content(role="user", parts=[types.Part(inline_data=types.Blob(data=audio_data, mime_type="audio/pcm"))])],
                        turn_complete=True,
                    )
                    transcription_parts = []
                    async for response in session.receive():
                        if response.server_content and response.server_content.output_transcription:
                            text = response.server_content.output_transcription.text
                            if text:
                                transcription_parts.append(text)
                        if response.server_content and response.server_content.turn_complete:
                            break
                    user_text = "".join(transcription_parts)
                    if user_text:
                        result = await _run_graph(user_text, thread_id, business_id, None, user_id, send_fn=send)
                        moa_response = result.get("text", "")
                        await _send_msg("message", moa_response, result.get("input"), result.get("extracted"))
                        if session:
                            try:
                                await session.send_client_content(
                                    turns=[types.Content(role="user", parts=[types.Part.from_text(text=moa_response)])],
                                    turn_complete=True,
                                )
                                async for resp in session.receive():
                                    if resp.data:
                                        await send({"type": "audio", "data": encode_audio(resp.data)})
                                    if resp.server_content and resp.server_content.turn_complete:
                                        await send({"type": "turn_complete"})
                                        break
                            except Exception:
                                await send({"type": "turn_complete"})
                                try:
                                    await session.__aexit__(None, None, None)
                                except Exception:
                                    pass
                                session = None
                except Exception as e:
                    logger.warning(f"Socket.IO audio error: {e}")
                    try:
                        await session.__aexit__(None, None, None)
                    except Exception:
                        pass
                    session = None

            elif kind == "end_turn":
                pass

    except Exception as e:
        logger.error(f"Socket.IO session error: {e}", exc_info=True)
        await send({"type": "error", "data": "Something went wrong."})
    finally:
        try:
            if session:
                await session.__aexit__(None, None, None)
        except Exception:
            pass
        logger.info("Socket.IO session closed")
