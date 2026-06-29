"""Voice provider base interface and factory."""

from __future__ import annotations

import logging
from typing import Protocol, AsyncIterator

logger = logging.getLogger(__name__)


class VoiceProvider(Protocol):
    """Protocol for voice providers (TTS + STT)."""

    async def connect(self) -> None:
        """Establish connections to TTS and STT services."""
        ...

    async def send_audio(self, chunk: bytes) -> None:
        """Send an audio chunk to the STT service for transcription."""
        ...

    async def get_transcription(self) -> str | None:
        """Get the latest final transcription (None if no complete turn yet)."""
        ...

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        """Stream TTS audio chunks for the given text."""
        ...

    async def disconnect(self) -> None:
        """Close all connections."""
        ...


def get_voice_provider() -> str:
    """Get the configured voice provider name."""
    from app.config.settings import settings
    return settings.voice_provider or "google"
