from __future__ import annotations

from typing import Any

from livekit.plugins import nvidia

from app.config.settings import settings


class VoiceResources:
    """Warm resources shared by  voice sessions."""

    def __init__(self) -> None:
        self._graph: Any = None
        self._stt: Any = None
        self._tts: Any = None

    def get(self) -> tuple[Any, Any, Any]:
        """Return initialized graph, STT, and TTS resources."""

        if self._graph is None:
            from app.graph.workflow import get_graph

            self._graph = get_graph()

        self._stt = nvidia.STT(
            api_key=settings.nvidia_api_key,
            language_code="en-US",
        )

        self._tts = nvidia.TTS(
            api_key=settings.nvidia_api_key,
            voice="Magpie-Multilingual.EN-US.Jason",
            language_code="en-US",
        )

        return (
            self._graph,
            self._stt,
            self._tts,
        )
