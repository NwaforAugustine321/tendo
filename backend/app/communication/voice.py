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


def _extract_thought(content: str) -> str:
    """Extract 'Thought:' text from agent ReAct format output."""
    if not content or "Thought:" not in content:
        return ""
    try:
        idx = content.index("Thought:")
        after = content[idx + 8:].strip()
        for marker in ["Action:", "Final Answer:", "\n\n"]:
            pos = after.find(marker)
            if pos != -1:
                after = after[:pos].strip()
                break
        return after[:200] if after else ""
    except (ValueError, IndexError):
        return ""


async def _run_graph(user_text: str, thread_id: str, business_id: str, websocket=None, user_id: str = "anonymous", send_fn=None) -> dict:
    from app.graph.workflow import get_graph

    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 25}

    from app.lib.thinking_status import get_thinking_status

    async def _send_thinking_msg(msg: str):
        if send_fn:
            try:
                if msg.startswith("__THOUGHT__:"):
                    thought_text = msg[12:]
                    await send_fn({"type": "thought", "data": thought_text})
                else:
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
        try:
            async for event in graph.astream(input_data, config=config, stream_mode="updates"):
                for node_name, node_output in event.items():
                    if node_name != "response":
                        msg = get_thinking_status(node_name)
                        await _send_thinking_msg(msg)

                    if isinstance(node_output, dict):
                        result.update(node_output)

                        # Extract and send thought text from agent raw output
                        messages = node_output.get("messages", [])
                        for m in messages:
                            if isinstance(m, dict) and m.get("role") == "assistant":
                                content = m.get("content", "")
                                thought = _extract_thought(content)
                                if thought:
                                    if send_fn:
                                        try:
                                            await send_fn({"type": "thought", "data": thought})
                                        except Exception:
                                            pass
        except Exception as e:
            logger.error(f"Graph execution error: {e}", exc_info=True)
            if send_fn:
                await send_fn({"type": "error", "data": "Something went wrong."})
        return result

    # Fresh invocation every time
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

    return response


async def _send_text_for_tts(session, text: str) -> bool:
    """Send text to Gemini Live for TTS playback. Returns False if session is dead."""
    if session is None:
        logger.warning("TTS skipped: session is None")
        return False
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

                # Always send text response to frontend first — this must never fail
                await _send_msg("message", moa_response, result.get("input"), result.get("extracted"))
                await send({"type": "turn_complete"})

                # TTS is best-effort — never crashes the connection
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
                                break
                    except Exception as e:
                        logger.warning(f"Socket.IO TTS failed (non-fatal): {e}")
                        try:
                            await session.__aexit__(None, None, None)
                        except Exception:
                            pass
                        session = None

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
