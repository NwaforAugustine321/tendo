"""Cartesia voice provider — WebSocket-based TTS and STT with turn detection.

Architecture:
- Single AsyncCartesia client, single STT connection, single TTS connection.
- All created once on first connect() call, reused forever.
- disconnect() is a no-op (connections stay alive).
- Server restart is the only thing that re-creates connections.

Requires:
- pip install cartesia
- CARTESIA_API_KEY env variable
- CARTESIA_VOICE_ID env variable
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from app.config.settings import settings

logger = logging.getLogger(__name__)

# ─── Module-level singleton state ───────────────────────────────────────────
_client = None
_stt_connection = None
_stt_cm = None
_tts_ws = None
_listener_task: asyncio.Task | None = None
_transcript_queue: asyncio.Queue[str] = asyncio.Queue()
_connected = False
_init_lock: asyncio.Lock | None = None


async def _ensure_connected():
    """Initialize the shared Cartesia connections once. No-op if already connected."""
    global _client, _stt_connection, _stt_cm, _tts_ws, _listener_task, _connected, _init_lock

    if _connected:
        return

    if _init_lock is None:
        _init_lock = asyncio.Lock()

    async with _init_lock:
        if _connected:
            return

        import cartesia

        _client = cartesia.AsyncCartesia(api_key=settings.cartesia_api_key)

        # Open single STT WebSocket
        stt_cm = _client.stt.auto_finalize.websocket(
            encoding="pcm_s16le",
            model=settings.cartesia_stt_model,
            sample_rate=16000,
        )
        _stt_connection = await stt_cm.__aenter__()
        _stt_cm = stt_cm

        # Open single TTS WebSocket
        _tts_ws = await _client.tts.websocket()
        await _tts_ws.connect()

        _connected = True

        # Start the single background STT listener
        _listener_task = asyncio.create_task(_listen_stt())

        logger.info("Cartesia singleton connections established (STT + TTS)")


async def _reconnect_stt():
    """Reconnect the STT WebSocket with exponential backoff."""
    global _stt_connection, _stt_cm, _connected

    backoff_delays = [1, 2, 4]
    for attempt, delay in enumerate(backoff_delays, 1):
        logger.warning(f"STT reconnection attempt {attempt}/{len(backoff_delays)}")
        try:
            stt_cm = _client.stt.auto_finalize.websocket(
                encoding="pcm_s16le",
                model=settings.cartesia_stt_model,
                sample_rate=16000,
            )
            _stt_connection = await stt_cm.__aenter__()
            _stt_cm = stt_cm
            logger.info("STT reconnected successfully")
            return True
        except Exception as e:
            error_str = str(e).lower()
            if "auth" in error_str or "401" in error_str or "403" in error_str:
                logger.error(f"STT auth error — not retrying: {e}")
                return False
            logger.warning(f"STT reconnection attempt {attempt} failed: {e}")
            if attempt < len(backoff_delays):
                await asyncio.sleep(delay)
    return False


async def _listen_stt():
    """Single background task: iterates over STT events, enqueues transcripts."""
    global _connected

    logger.info("STT listener started (singleton)")
    while _connected:
        try:
            async for event in _stt_connection:
                event_type = getattr(event, "type", None)
                if event_type == "turn.end":
                    transcript = getattr(event, "transcript", "")
                    if transcript:
                        logger.info(f"STT turn.end: {transcript[:80]}")
                        await _transcript_queue.put(transcript)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"STT listener error: {e}")
            if not await _reconnect_stt():
                _connected = False
                break
    logger.info("STT listener stopped")


class CartesiaVoiceProvider:
    """Cartesia TTS + STT provider — thin wrapper around module-level singletons.

    connect() ensures the shared connections exist (no-op if already up).
    disconnect() is a no-op — connections persist until server stops.
    """

    def __init__(self) -> None:
        self._voice_id = settings.cartesia_voice_id
        self._tts_model = settings.cartesia_tts_model
        self._language = settings.cartesia_language

    async def connect(self) -> None:
        """Ensure shared connections are alive. Creates them on first call."""
        try:
            await _ensure_connected()
        except ImportError:
            raise ImportError("cartesia package not installed. Run: pip install cartesia")
        except Exception as e:
            logger.error(f"Failed to connect Cartesia: {e}")
            raise

    async def send_audio(self, chunk: bytes) -> None:
        """Send audio chunk to the shared STT connection."""
        if not _connected or not _stt_connection:
            return
        try:
            await _stt_connection.send_raw(chunk)
        except Exception as e:
            logger.error(f"Failed to send audio to STT: {e}")

    async def get_transcription(self) -> str | None:
        """Get the latest final transcription from the shared queue."""
        try:
            return _transcript_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        """Stream TTS audio chunks using the shared TTS WebSocket."""
        if not _tts_ws:
            return

        try:
            ctx = _tts_ws.context()
            await ctx.send(
                model_id=self._tts_model,
                transcript=text,
                voice={"mode": "id", "id": self._voice_id},
                language=self._language,
                output_format={
                    "container": "raw",
                    "encoding": "pcm_s16le",
                    "sample_rate": 24000,
                },
                continue_=False,
            )
            async for chunk in ctx.receive():
                chunk_type = getattr(chunk, "type", None)
                if chunk_type == "chunk" and hasattr(chunk, "audio") and chunk.audio:
                    yield chunk.audio
        except Exception as e:
            logger.error(f"Cartesia TTS error: {e}", exc_info=True)

    async def disconnect(self) -> None:
        """No-op — shared connections persist until server stops."""
        pass
