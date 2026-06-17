"""Voice module — real-time streaming and one-shot voice operations."""

import asyncio
import logging
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

from app.ws.connection import accept, close
from app.ws.sender import send_audio, send_transcript, send_turn_complete, send_error
from app.ws.receiver import receive_json
from app.ws.encoding import decode_audio
from app.config.settings import settings

logger = logging.getLogger(__name__)
SPECS_DIR = Path(__file__).parent / "specs"


def _load_instruction() -> str:
    parts = []
    for name in ["role", "backstory", "goal", "skill"]:
        file = SPECS_DIR / f"{name}.md"
        if file.exists():
            content = file.read_text(encoding="utf-8").strip()
            if content:
                parts.append(content)
    return "\n\n".join(parts)


def _get_client():
    return genai.Client(api_key=settings.google_voice_api_key)


def _get_config() -> types.LiveConnectConfig:
    instruction = _load_instruction()

    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        output_audio_transcription=types.AudioTranscriptionConfig(),
        system_instruction=types.Content(
            parts=[types.Part.from_text(text=instruction)]
        ),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
            )
        ),
    )


async def handle_session(websocket: WebSocket):
    """
    Voice session using the same pattern as the working snippet:
    - Collect all audio until end_turn
    - Send as one blob with turn_complete=True
    - Then read response stream
    - Repeat
    """
    await accept(websocket)
    logger.info("Voice WebSocket accepted")

    client = _get_client()
    config = _get_config()
    logger.info(f"Connecting to model: {settings.google_voice_model}")

    try:
        async with client.aio.live.connect(
            model=settings.google_voice_model, config=config
        ) as session:
            logger.info("AI session connected")

            while True:
                # 1. Collect input from browser (buffer audio until end_turn or text)
                input_result = await _collect_input(websocket)

                if input_result is None:
                    break  # Client disconnected

                input_type, data = input_result

                # 2. Send to AI as one complete turn
                if input_type == "audio":
                    logger.info(f"Sending audio: {len(data)} bytes")
                    await session.send(
                        input=types.LiveClientContent(
                            turns=[
                                types.Content(
                                    role="user",
                                    parts=[
                                        types.Part(
                                            inline_data=types.Blob(
                                                data=data, mime_type="audio/pcm"
                                            )
                                        )
                                    ],
                                )
                            ],
                            turn_complete=True,
                        )
                    )
                elif input_type == "text":
                    logger.info(f"Text input: {data[:50]}")

                    # Text goes through MOA agent
                    from app.agents.moa import process as moa_process
                    result = await moa_process(
                        user_message=data,
                        thread_id="default",
                        business_id="default",
                        conversation_history=[],
                    )
                    moa_response = result["response"]
                    logger.info(f"MOA response: {moa_response[:80]}")

                    # Send MOA response to Gemini for TTS
                    await session.send(
                        input=types.LiveClientContent(
                            turns=[
                                types.Content(
                                    role="user",
                                    parts=[types.Part.from_text(text=f"Read this aloud exactly: {moa_response}")],
                                )
                            ],
                            turn_complete=True,
                        )
                    )

                # 3. Stream back the AI response
                logger.info("Waiting for AI response...")
                async for response in session.receive():
                    if response.data:
                        await send_audio(websocket, response.data)

                    if (
                        response.server_content
                        and response.server_content.output_transcription
                    ):
                        text = response.server_content.output_transcription.text
                        if text:
                            logger.info(f"AI: {text[:80]}")
                            await send_transcript(websocket, text)

                    if response.server_content and response.server_content.turn_complete:
                        logger.info("AI turn complete")
                        await send_turn_complete(websocket)
                        break

                # Small pause between turns (matches working snippet)
                await asyncio.sleep(0.3)

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Session error: {e}", exc_info=True)
        await send_error(websocket, str(e))
    finally:
        await close(websocket)
        logger.info("WebSocket closed")


async def _collect_input(websocket: WebSocket) -> tuple[str, bytes | str] | None:
    """
    Collect user input from browser.
    For audio: buffers all chunks until end_turn, returns concatenated bytes.
    For text: returns immediately.
    Returns None if client disconnects.
    """
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
                # Concatenate all audio chunks into one blob
                full_audio = b"".join(audio_buffer)
                logger.info(f"Audio collected: {len(full_audio)} bytes from {len(audio_buffer)} chunks")
                return ("audio", full_audio)
            # end_turn with no audio — ignore
            continue

        elif kind == "text":
            return ("text", message.get("data", ""))


async def transcribe(audio_bytes: bytes, timeout: float = 10.0) -> str:
    """Convert audio to text (one-shot)."""
    raise NotImplementedError("Not yet implemented")


async def synthesize(text: str, timeout: float = 10.0) -> bytes:
    """Convert text to audio (one-shot)."""
    raise NotImplementedError("Not yet implemented")
