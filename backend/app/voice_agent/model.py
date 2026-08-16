from __future__ import annotations

from typing import Any


class VoiceSessionData:
    """
    Data required to initialize a voice session.

    Accepts any key-value pairs from metadata and exposes them
    as attributes via __getattr__.
    """

    def __init__(self, **kwargs: Any) -> None:
        self._data: dict[str, Any] = kwargs

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return self._data.get(name, "")

    def __repr__(self) -> str:
        return f"VoiceSessionData({self._data})"

    def __str__(self) -> str:
        return str(self._data)

    def get(self, key: str, default: Any = "") -> Any:
        return self._data.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)

    @property
    def communication_id(self) -> str:
        """
        Return the identifier used for application communication.

        Prefer the chat session ID when available. Otherwise,
        use the business ID for business-level communication.
        """

        return self._data.get("session_id", "") or self._data.get("business_id", "")


class InvalidVoiceSessionMetadata(Exception):
    """Raised when voice session metadata is missing or invalid."""
