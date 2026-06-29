"""Google Gemini Live voice provider.

Architecture:
- genai.Client is a singleton (created once, cheap to hold).
- Gemini Live session is per-user-session (Google closes idle sessions quickly).
- connect() opens a fresh session, disconnect() closes it.
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from app.config.settings import settings

logger = logging.getLogger(__name__)

# ─── Shared client singleton (stateless, never closes) ──────────────────────
_client = None
_client_lock: asyncio.Lock | None = None


async def _get_client():
    """Get or create the shared genai.Client (singleton)."""
    global _client, _client_lock

    if _client is not None:
        return _client

    if _client_lock is None:
        _client_lock = asyncio.Lock()

    async with _client_lock:
        if _client is not None:
            return _client
        from google import genai
        _client = genai.Client(api_key=settings.google_voice_api_key)
        logger.info("Google genai client initialized (singleton)")
        return _client


class GoogleVoiceProvider:
    """Google Gemini Live API provider.

    Client is shared (singleton). Session is per-user (Google has short idle timeouts).
    """

    def __init__(self) -> None:
        self._session = None
        self._connected = False
        self._transcript_queue: asyncio.Queue[str] = asyncio.Queue()

    async def connect(self) -> None:
        """Open a fresh Gemini Live session."""
        try:
            from google.genai import types

            client = await _get_client()

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

            self._session = await client.aio.live.connect(
                model=settings.google_voice_model, config=config
            ).__aenter__()

            self._connected = True
            logger.info("Google Gemini session connected")
        except Exception as e:
            logger.error(f"Failed to connect Google session: {e}")
            raise

    async def send_audio(self, chunk: bytes) -> None:
        """Send audio chunk to Gemini for transcription."""
        if not self._connected or not self._session:
            return

        try:
            from google.genai import types

            await self._session.send_client_content(
                turns=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                inline_data=types.Blob(data=chunk, mime_type="audio/pcm")
                            )
                        ],
                    )
                ],
                turn_complete=True,
            )

            transcription_parts = []
            async for response in self._session.receive():
                if (
                    response.server_content
                    and response.server_content.output_transcription
                ):
                    text = response.server_content.output_transcription.text
                    if text:
                        transcription_parts.append(text)
                if response.server_content and response.server_content.turn_complete:
                    break

            transcript = "".join(transcription_parts)
            if transcript:
                await self._transcript_queue.put(transcript)

        except Exception as e:
            error_str = str(e).lower()
            if "1000" in error_str or "closed" in error_str:
                logger.warning("Google session closed, reconnecting...")
                self._connected = False
                self._session = None
                try:
                    await self.connect()
                except Exception:
                    pass
            else:
                logger.error(f"Google send_audio error: {e}")

    async def get_transcription(self) -> str | None:
        """Get the latest final transcription."""
        try:
            return self._transcript_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        """Send text to Gemini for TTS and yield audio chunks."""
        if not self._connected or not self._session:
            return

        try:
            from google.genai import types

            await self._session.send_client_content(
                turns=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=text)]
                    )
                ],
                turn_complete=True,
            )

            async for response in self._session.receive():
                if response.data:
                    yield response.data
                if response.server_content and response.server_content.turn_complete:
                    break

        except Exception as e:
            error_str = str(e).lower()
            if "1000" in error_str or "closed" in error_str:
                logger.warning("Google session closed during TTS")
                self._connected = False
                self._session = None
            else:
                logger.error(f"Google TTS error: {e}")

    async def disconnect(self) -> None:
        """Close the per-user Gemini Live session."""
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
            self._session = None
        self._connected = False
        logger.info("Google Gemini session disconnected")
