from __future__ import annotations

from typing import Any

from livekit.plugins import nvidia

from app.config.settings import settings


class VoiceResources:

    def get_stt(self) -> Any:
        return nvidia.STT(
            api_key=settings.nvidia_api_key,
            language_code="en-US",
        )

    def get_tts(self) -> Any:
        return nvidia.TTS(
            api_key=settings.nvidia_api_key,
            voice="Magpie-Multilingual.EN-US.Jason",
            language_code="en-US",
        )

    def get(self) -> tuple[Any, Any]:
        return (
            self.get_stt(),
            self.get_tts(),
        )
