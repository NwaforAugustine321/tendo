"""Custom streaming TTS for LiveKit AgentSession using Riva TTS."""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

import riva.client
from livekit.agents import tts

from app.config.settings import settings

logger = logging.getLogger(__name__)

GRPC_URI = "grpc.nvcf.nvidia.com:443"


class Tts(tts.TTS):

    def __init__(self, *, language: str = "en-US", voice: str | None = None, sample_rate: int = 16000) -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=True),
            sample_rate=sample_rate,
            num_channels=1,
        )
        self._language = language
        self._voice = voice or settings.tts_voice
        self._sample_rate = sample_rate

        metadata = [
            ("function-id", settings.tts_function_id),
            ("authorization", f"Bearer {settings.nvidia_api_key}"),
        ]
        self._auth = riva.client.Auth(uri=GRPC_URI, use_ssl=True, metadata_args=metadata)
        self._tts_service = riva.client.SpeechSynthesisService(self._auth)

    def synthesize(self, text: str) -> "CustomTtsStream":
        return CustomTtsStream(
            tts_service=self._tts_service,
            text=text,
            language=self._language,
            voice=self._voice,
            sample_rate=self._sample_rate,
        )


class CustomTtsStream(tts.SynthesizeStream):

    def __init__(self, *, tts_service, text: str, language: str, voice: str, sample_rate: int) -> None:
        super().__init__()
        self._tts_service = tts_service
        self._text = text
        self._language = language
        self._voice = voice
        self._sample_rate = sample_rate

    async def collect(self) -> tts.SynthesizedAudio:
        try:
            response = await asyncio.to_thread(
                self._tts_service.synthesize,
                self._text,
                self._voice,
                self._language,
                sample_rate_hz=self._sample_rate,
                encoding=riva.client.AudioEncoding.LINEAR_PCM,
            )
            return tts.SynthesizedAudio(data=response.audio, sample_rate=self._sample_rate, num_channels=1)
        except Exception as e:
            logger.error(f"[CustomTts] synthesis error: {e}")
            return tts.SynthesizedAudio(data=b"", sample_rate=self._sample_rate, num_channels=1)

    async def _run(self) -> AsyncIterator[tts.SynthesizedAudio]:
        try:
            responses = await asyncio.to_thread(
                self._tts_service.synthesize_online,
                self._text,
                self._voice,
                self._language,
                sample_rate_hz=self._sample_rate,
                encoding=riva.client.AudioEncoding.LINEAR_PCM,
            )
            for resp in responses:
                if resp.audio:
                    yield tts.SynthesizedAudio(data=resp.audio, sample_rate=self._sample_rate, num_channels=1)
        except Exception as e:
            logger.error(f"[CustomTts] streaming synthesis error: {e}")
