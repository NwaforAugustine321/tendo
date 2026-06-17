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
    """Load system instruction from spec .md files (role → backstory → goal → skill)."""
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
    """Build live config with instruction loaded from spec files."""
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
    """Full-duplex voice session between browser and AI."""
    await accept(websocket)
    logger.info("Voice WebSocket accepted")

    client = _get_client()
    config = _get_config()
    logger.info("Instruction loaded, connecting to AI...")

    try:
        async with client.aio.live.connect(
            model="gemini-2.0-flash-live-001", config=config
        ) as session:
            logger.info("AI session connected successfully")
            receive_task = asyncio.create_task(_receive(websocket, session))
            stream_task = asyncio.create_task(_stream(websocket, session))

            done, pending = await asyncio.wait(
                [receive_task, stream_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            for task in done:
                exc = task.exception()
                if exc:
                    logger.error(f"Task error: {exc}", exc_info=exc)

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Voice session error: {e}", exc_info=True)
        await send_error(websocket, str(e))
    finally:
        await close(websocket)
        logger.info("Voice WebSocket closed")


async def _receive(websocket: WebSocket, session):
    """Receive from browser, forward to AI."""
    try:
        while True:
            message = await receive_json(websocket)
            if message is None:
                logger.info("Browser disconnected (receive returned None)")
                break

            kind = message.get("type")
            logger.info(f"Received from browser: type={kind}")

            if kind == "audio":
                raw = decode_audio(message["data"])
                logger.debug(f"Audio chunk: {len(raw)} bytes")
                await session.send(
                    input=types.LiveClientContent(
                        turns=[
                            types.Content(
                                role="user",
                                parts=[
                                    types.Part(
                                        inline_data=types.Blob(
                                            data=raw, mime_type="audio/pcm"
                                        )
                                    )
                                ],
                            )
                        ],
                        turn_complete=False,
                    )
                )

            elif kind == "text":
                logger.info(f"Text input: {message.get('data', '')[:50]}")
                await session.send(
                    input=types.LiveClientContent(
                        turns=[
                            types.Content(
                                role="user",
                                parts=[types.Part.from_text(text=message["data"])],
                            )
                        ],
                        turn_complete=True,
                    )
                )

            elif kind == "end_turn":
                logger.info("End turn signal received, signaling AI")
                await session.send(
                    input=types.LiveClientContent(turn_complete=True)
                )

    except (WebSocketDisconnect, asyncio.CancelledError):
        logger.info("_receive task ended")
    except Exception as e:
        logger.error(f"_receive error: {e}", exc_info=True)


async def _stream(websocket: WebSocket, session):
    """Stream AI responses back to browser. Keeps listening for multiple turns."""
    try:
        while True:
            logger.info("Waiting for AI response...")
            async for response in session.receive():
                if response.data:
                    logger.debug(f"AI audio chunk: {len(response.data)} bytes")
                    await send_audio(websocket, response.data)

                if (
                    response.server_content
                    and response.server_content.output_transcription
                ):
                    text = response.server_content.output_transcription.text
                    if text:
                        logger.info(f"AI transcript: {text[:50]}")
                        await send_transcript(websocket, text)

                if response.server_content and response.server_content.turn_complete:
                    logger.info("AI turn complete")
                    await send_turn_complete(websocket)
                    break

    except (WebSocketDisconnect, asyncio.CancelledError):
        logger.info("_stream task ended")
    except Exception as e:
        logger.error(f"_stream error: {e}", exc_info=True)


async def transcribe(audio_bytes: bytes, timeout: float = 10.0) -> str:
    """Convert audio to text (one-shot)."""
    raise NotImplementedError("One-shot transcription not yet implemented")


async def synthesize(text: str, timeout: float = 10.0) -> bytes:
    """Convert text to audio (one-shot)."""
    raise NotImplementedError("One-shot synthesis not yet implemented")
