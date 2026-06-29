"""Voice module — real-time streaming and one-shot voice operations."""

import asyncio
import logging
import re

from fastapi import WebSocket, WebSocketDisconnect

from app.ws.connection import accept, close
from app.ws.sender import send_audio, send_message, send_turn_complete, send_error, send_thinking
from app.ws.receiver import receive_json
from app.ws.encoding import decode_audio
from app.config.settings import settings
from app.services.auth import handle_get_me, COOKIE_NAME

logger = logging.getLogger(__name__)

# Per-thread conversation history — maps thread_id to message list
_thread_histories: dict[str, list[dict]] = {}


def _clean_text(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[-*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text.strip()


async def _run_graph(user_text: str, thread_id: str, business_id: str, websocket=None, user_id: str = "anonymous", send_fn=None) -> dict:
    from app.graph.workflow import get_graph

    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 25}

    from app.lib.thinking_status import get_thinking_status

    # Maintain per-thread conversation history (last 12 messages)
    if thread_id not in _thread_histories:
        _thread_histories[thread_id] = []
    thread_messages = _thread_histories[thread_id]

    async def _send_thinking_msg(msg):
        """Send thinking/thought to frontend. Accepts str or dict."""
        if send_fn:
            try:
                if isinstance(msg, dict):
                    # From ThinkingStreamCallback — already formatted
                    await send_fn(msg)
                elif isinstance(msg, str):
                    await send_fn({"type": "thinking", "data": msg})
            except Exception:
                pass
        elif websocket:
            try:
                text = msg.get("data", "") if isinstance(msg, dict) else msg
                await send_thinking(websocket, text)
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

                        # Thought extraction is handled in agent executor via callback
        except Exception as e:
            logger.error(f"Graph execution error: {e}", exc_info=True)
            if send_fn:
                await send_fn({"type": "error", "data": "Something went wrong."})
        return result

    # Fresh invocation every time — include conversation history
    input_state = {
        "event": {"text": user_text, "thread_id": thread_id, "business_id": business_id},
        "thread_id": thread_id,
        "business_id": business_id,
        "user_id": user_id,
        "messages": thread_messages[-12:],
        "thinking_callback": _send_thinking_msg,
    }
    result = await _stream_invoke(input_state)

    # Update thread history with new messages from this turn
    new_messages = result.get("messages", [])
    if new_messages:
        thread_messages.extend(new_messages)
        # Keep only last 24 messages to prevent unbounded growth
        if len(thread_messages) > 24:
            _thread_histories[thread_id] = thread_messages[-24:]

    response = result.get("response") or {}
    response["text"] = _clean_text(response.get("text", ""))
    response["input"] = response.get("input")
    response["extracted"] = response.get("extracted")

    return response


async def handle_session(websocket: WebSocket):
    """Provider-agnostic voice WebSocket session handler.

    Uses the VoiceProvider interface to delegate all STT/TTS operations.
    Provider selection happens at session startup based on settings.voice_provider.
    """
    await accept(websocket)
    logger.info("Voice WebSocket accepted")

    # Auth
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

    thread_id = websocket.query_params.get("session_id", "")
    business_id = websocket.query_params.get("business_id", "")

    # Create provider-agnostic voice provider
    from app.communication.providers import create_voice_provider
    provider = create_voice_provider()

    try:
        await provider.connect()
        logger.info(f"Voice provider connected: {settings.voice_provider}")
        await send_turn_complete(websocket)

        if settings.voice_provider == "cartesia":
            # Cartesia mode: continuous audio streaming with server-side turn detection
            await _handle_cartesia_session(websocket, provider, thread_id, business_id, user_id)
        else:
            # Google mode: preserve existing end_turn collection flow
            await _handle_google_session(websocket, provider, thread_id, business_id, user_id)

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Session error: {e}", exc_info=True)
        await send_error(websocket, "Something went wrong. Please try again.")
    finally:
        await provider.disconnect()
        await close(websocket)
        logger.info("WebSocket closed")


async def _handle_cartesia_session(websocket: WebSocket, provider, thread_id: str, business_id: str, user_id: str | None):
    """Handle Cartesia voice session — continuous streaming with server-side turn detection."""
    is_speaking = False

    async def _audio_sender():
        """Continuously receive audio from client and forward to provider."""
        nonlocal is_speaking
        while True:
            message = await receive_json(websocket)
            if message is None:
                break
            kind = message.get("type")
            if kind == "audio":
                # Don't send audio to STT while TTS is playing (prevents feedback)
                if not is_speaking:
                    raw = decode_audio(message["data"])
                    await provider.send_audio(raw)
            elif kind == "text":
                user_text = message.get("data", "")
                if user_text:
                    await send_thinking(websocket, "Processing...")
                    result = await _run_graph(user_text, thread_id, business_id, websocket, user_id)
                    moa_response = result.get("text", "")
                    await send_message(websocket, moa_response, result.get("input"), result.get("extracted"))
                    is_speaking = True
                    try:
                        async for audio_chunk in provider.synthesize(moa_response):
                            await send_audio(websocket, audio_chunk)
                    finally:
                        is_speaking = False
                    await send_turn_complete(websocket)

    async def _transcription_poller():
        """Poll for completed transcriptions from provider and process them."""
        nonlocal is_speaking
        while True:
            transcript = await provider.get_transcription()
            if transcript:
                # Ignore transcripts from echo while TTS is playing
                if is_speaking:
                    continue
                logger.info(f"Transcribed: {transcript[:80]}")
                await send_thinking(websocket, "Processing...")
                result = await _run_graph(transcript, thread_id, business_id, websocket, user_id)
                moa_response = result.get("text", "")
                logger.info(f"Response: {moa_response[:80]}")
                await send_message(websocket, moa_response, result.get("input"), result.get("extracted"))
                is_speaking = True
                try:
                    async for audio_chunk in provider.synthesize(moa_response):
                        await send_audio(websocket, audio_chunk)
                finally:
                    is_speaking = False
                await send_turn_complete(websocket)
            else:
                await asyncio.sleep(0.1)

    # Run audio sender and transcription poller concurrently
    sender_task = asyncio.create_task(_audio_sender())
    poller_task = asyncio.create_task(_transcription_poller())

    try:
        # Wait for the sender to finish (client disconnect)
        await sender_task
    finally:
        poller_task.cancel()
        try:
            await poller_task
        except asyncio.CancelledError:
            pass


async def _handle_google_session(websocket: WebSocket, provider, thread_id: str, business_id: str, user_id: str | None):
    """Handle Google Gemini voice session — uses end_turn collection flow."""
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
            await provider.send_audio(data)
            # Wait a moment for transcription to be processed
            await asyncio.sleep(0.5)
            user_text = await provider.get_transcription() or ""
            logger.info(f"Transcribed: {user_text[:80]}")

        if not user_text:
            continue

        result = await _run_graph(user_text, thread_id, business_id, websocket, user_id)
        moa_response = result.get("text", "")
        logger.info(f"Response: {moa_response[:80]}")

        await send_message(websocket, moa_response, result.get("input"), result.get("extracted"))

        # TTS
        async for audio_chunk in provider.synthesize(moa_response):
            await send_audio(websocket, audio_chunk)
        await send_turn_complete(websocket)

        await asyncio.sleep(0.3)


async def _collect_input(websocket: WebSocket) -> tuple[str, bytes | str] | None:
    """Collect user input — waits for end_turn signal to batch audio chunks."""
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
    from app.communication.providers import create_voice_provider

    thread_id = session_id
    provider = create_voice_provider()

    async def _send_msg(text: str = "", questions=None, extracted=None):
        msg = {"type": "message", "data": {"response": text, "msg_type": "answer"}}
        if questions:
            msg["data"]["msg_type"] = "question"
            msg["data"]["questions"] = questions
        if extracted:
            msg["data"]["extracted"] = extracted
        await send(msg)

    try:
        await provider.connect()
        logger.info(f"Socket.IO: Voice provider connected ({settings.voice_provider})")
        await send({"type": "turn_complete"})

        if settings.voice_provider == "cartesia":
            await _run_socketio_cartesia(provider, thread_id, business_id, user_id, receive, send, _send_msg, decode_audio, encode_audio)
        else:
            await _run_socketio_google(provider, thread_id, business_id, user_id, receive, send, _send_msg, decode_audio, encode_audio)

    except Exception as e:
        logger.error(f"Socket.IO session error: {e}", exc_info=True)
        await send({"type": "error", "data": "Something went wrong."})
    finally:
        await provider.disconnect()
        logger.info("Socket.IO session closed")


async def _run_socketio_cartesia(provider, thread_id, business_id, user_id, receive, send, _send_msg, decode_audio, encode_audio):
    """Socket.IO Cartesia mode — continuous streaming with server-side turn detection."""
    # Mute flag: prevents mic audio from being sent to STT while TTS is playing.
    # This avoids the feedback loop where Cartesia transcribes its own TTS output.
    is_speaking = False

    async def _message_handler():
        """Handle incoming messages from client."""
        nonlocal is_speaking
        while True:
            message = await receive()
            if message is None:
                break
            kind = message.get("type")
            if kind == "audio":
                # Don't forward audio to STT while TTS is playing (prevents echo)
                if not is_speaking:
                    audio_data = decode_audio(message.get("data", ""))
                    await provider.send_audio(audio_data)
            elif kind == "text":
                user_text = message.get("data", "")
                if user_text:
                    logger.info(f"Socket.IO text: {user_text[:50]}")
                    await send({"type": "thinking", "data": "Processing..."})
                    result = await _run_graph(user_text, thread_id, business_id, None, user_id, send_fn=send)
                    moa_response = result.get("text", "")
                    await _send_msg(moa_response, result.get("input"), result.get("extracted"))
                    # TTS — mute STT while speaking
                    is_speaking = True
                    try:
                        async for audio_chunk in provider.synthesize(moa_response):
                            await send({"type": "audio", "data": encode_audio(audio_chunk)})
                    finally:
                        is_speaking = False
                    await send({"type": "turn_complete"})

    async def _transcription_poller():
        """Poll for transcriptions and process them."""
        nonlocal is_speaking
        while True:
            transcript = await provider.get_transcription()
            if transcript:
                # Ignore transcripts that arrive while TTS is playing (echo from speaker)
                if is_speaking:
                    logger.debug(f"Ignoring echo transcript: {transcript[:40]}")
                    continue
                logger.info(f"Socket.IO transcribed: {transcript[:80]}")
                await send({"type": "thinking", "data": "Processing..."})
                result = await _run_graph(transcript, thread_id, business_id, None, user_id, send_fn=send)
                moa_response = result.get("text", "")
                logger.info(f"Socket.IO response: {moa_response[:80]}")
                await _send_msg(moa_response, result.get("input"), result.get("extracted"))
                # TTS — mute STT while speaking
                is_speaking = True
                try:
                    async for audio_chunk in provider.synthesize(moa_response):
                        await send({"type": "audio", "data": encode_audio(audio_chunk)})
                finally:
                    is_speaking = False
                await send({"type": "turn_complete"})
            else:
                await asyncio.sleep(0.1)

    handler_task = asyncio.create_task(_message_handler())
    poller_task = asyncio.create_task(_transcription_poller())

    try:
        await handler_task
    finally:
        poller_task.cancel()
        try:
            await poller_task
        except asyncio.CancelledError:
            pass


async def _run_socketio_google(provider, thread_id, business_id, user_id, receive, send, _send_msg, decode_audio, encode_audio):
    """Socket.IO Google mode — uses Gemini Live session directly.

    Google Gemini Live requires: collect audio → send as one blob → wait for response.
    Individual chunk streaming doesn't work (session closes immediately).
    """
    from google import genai
    from google.genai import types

    client = await _get_google_client()
    config = types.LiveConnectConfig(
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

    session = await client.aio.live.connect(
        model=settings.google_voice_model, config=config
    ).__aenter__()
    logger.info("Google Gemini session ready (Socket.IO)")

    try:
        while True:
            message = await receive()
            if message is None:
                break

            kind = message.get("type")

            if kind == "text":
                user_text = message.get("data", "")
                if not user_text:
                    continue
                logger.info(f"Socket.IO text: {user_text[:50]}")
                await send({"type": "thinking", "data": "Processing..."})

                result = await _run_graph(user_text, thread_id, business_id, None, user_id, send_fn=send)
                moa_response = result.get("text", "")
                logger.info(f"Socket.IO response: {moa_response[:80]}")

                await _send_msg(moa_response, result.get("input"), result.get("extracted"))
                await send({"type": "turn_complete"})

                # TTS via Gemini session
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
                        # Session died — recreate
                        try:
                            await session.__aexit__(None, None, None)
                        except Exception:
                            pass
                        session = await client.aio.live.connect(
                            model=settings.google_voice_model, config=config
                        ).__aenter__()

            elif kind == "audio":
                # Stream audio to Gemini immediately (keeps session alive)
                chunk_data = decode_audio(message.get("data", ""))
                if session:
                    try:
                        await session.send_client_content(
                            turns=[types.Content(role="user", parts=[
                                types.Part(inline_data=types.Blob(data=chunk_data, mime_type="audio/pcm"))
                            ])],
                            turn_complete=False,
                        )
                    except Exception:
                        # Session died during streaming — will reconnect at end_turn
                        session = None

            elif kind == "end_turn":
                await send({"type": "thinking", "data": "Processing..."})

                # If session died, reconnect
                if not session:
                    try:
                        session = await client.aio.live.connect(
                            model=settings.google_voice_model, config=config
                        ).__aenter__()
                    except Exception as e:
                        logger.error(f"Failed to reconnect Gemini: {e}")
                        await send({"type": "turn_complete"})
                        continue

                # Signal turn complete — Gemini will now produce a transcription
                try:
                    await session.send_client_content(
                        turns=[],
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
                except Exception as e:
                    logger.debug(f"Transcription failed (will retry next turn): {e}")
                    user_text = ""
                    try:
                        await session.__aexit__(None, None, None)
                    except Exception:
                        pass
                    session = None

                if not user_text:
                    await send({"type": "turn_complete"})
                    continue

                logger.info(f"Transcribed: {user_text[:80]}")
                result = await _run_graph(user_text, thread_id, business_id, None, user_id, send_fn=send)
                moa_response = result.get("text", "")
                await _send_msg(moa_response, result.get("input"), result.get("extracted"))

                # TTS
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
                    except Exception:
                        try:
                            await session.__aexit__(None, None, None)
                        except Exception:
                            pass
                        session = None

                await send({"type": "turn_complete"})

    finally:
        if session:
            try:
                await session.__aexit__(None, None, None)
            except Exception:
                pass


async def _get_google_client():
    """Get or create the shared Google client."""
    from app.communication.providers.google_provider import _get_client
    return await _get_client()
