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
    """Full-duplex voice session."""
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

            # Two independent loops running concurrently
            receive_task = asyncio.create_task(_receive_loop(websocket, session))
            stream_task = asyncio.create_task(_stream_loop(websocket, session))

            done, pending = await asyncio.wait(
                [receive_task, stream_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            for task in done:
                exc = task.exception()
                if exc:
                    logger.error(f"Task error: {exc}", exc_info=exc)

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Session error: {e}", exc_info=True)
        await send_error(websocket, str(e))
    finally:
        await close(websocket)
        logger.info("WebSocket closed")


async def _receive_loop(websocket: WebSocket, session):
    """Continuously receive from browser and forward to AI session."""
    try:
        while True:
            message = await receive_json(websocket)
            if message is None:
                logger.info("Browser disconnected")
                return

            kind = message.get("type")

            if kind == "audio":
                raw = decode_audio(message["data"])
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
                logger.info(f"Text: {message.get('data', '')[:50]}")
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
                logger.info("End turn signal")
                await session.send(
                    input=types.LiveClientContent(turn_complete=True)
                )

    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as e:
        logger.error(f"receive_loop error: {e}", exc_info=True)


async def _stream_loop(websocket: WebSocket, session):
    """Continuously stream AI responses back to browser. Never exits on turn_complete."""
    try:
        async for response in session.receive():
            # Audio data
            if response.data:
                await send_audio(websocket, response.data)

            # Transcript text
            if response.server_content and response.server_content.output_transcription:
                text = response.server_content.output_transcription.text
                if text:
                    logger.info(f"AI: {text[:80]}")
                    await send_transcript(websocket, text)

            # Turn complete — notify browser but keep listening
            if response.server_content and response.server_content.turn_complete:
                logger.info("AI turn complete")
                await send_turn_complete(websocket)
                # Do NOT break — keep the iterator alive for next turn

    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as e:
        logger.error(f"stream_loop error: {e}", exc_info=True)


async def transcribe(audio_bytes: bytes, timeout: float = 10.0) -> str:
    """Convert audio to text (one-shot)."""
    raise NotImplementedError("Not yet implemented")


async def synthesize(text: str, timeout: float = 10.0) -> bytes:
    """Convert text to audio (one-shot)."""
    raise NotImplementedError("Not yet implemented")
