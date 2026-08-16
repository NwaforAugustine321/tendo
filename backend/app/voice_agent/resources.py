from __future__ import annotations

from typing import Any

from livekit.plugins import nvidia

from app.config.settings import settings


class VoiceResources:
    """Provides resources for voice sessions."""

    def __init__(self) -> None:
        self._graph: Any = None

    def get_graph(self) -> Any:
        """Return the shared graph instance."""

        if self._graph is None:
            from app.graph.workflow import get_graph

            self._graph = get_graph()

        return self._graph

    def get_stt(self) -> Any:
        """Create a fresh NVIDIA STT instance."""

        return nvidia.STT(
            api_key=settings.nvidia_api_key,
            language_code="en-US",
        )

    def get_tts(self) -> Any:
        """Create a fresh NVIDIA TTS instance."""

        return nvidia.TTS(
            api_key=settings.nvidia_api_key,
            voice="Magpie-Multilingual.EN-US.Jason",
            language_code="en-US",
        )

    def get(self) -> tuple[Any, Any, Any]:
        """Return graph and fresh STT/TTS resources."""

        return (
            self.get_graph(),
            self.get_stt(),
            self.get_tts(),
        )
