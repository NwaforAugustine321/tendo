from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SocketConnection:
    """Application identity associated with a Socket.IO connection."""

    sid: str
    session_id: str = ""
    business_id: str = ""
    user_id: str = ""


@dataclass(frozen=True, slots=True)
class SocketTextInput:
    """Text content received from the frontend."""

    content: str
    session_id: str = ""
    record_id: str = ""

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
    ) -> SocketTextInput:
        """Create text input from a Socket.IO payload."""

        return cls(
            content=payload.get(
                "content",
                "",
            ),
            session_id=payload.get(
                "session_id",
                "",
            ),
            record_id=payload.get(
                "record_id",
                "",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the text input to a payload dictionary."""

        return {
            "content": self.content,
            "session_id": self.session_id,
            "record_id": self.record_id,
        }


@dataclass(frozen=True, slots=True)
class SocketResponse:
    """Response content sent to the frontend."""

    content: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the response to a payload dictionary."""

        return {
            "content": self.content,
        }


@dataclass(frozen=True, slots=True)
class SocketMessage:
    """
    Generic Socket.IO message envelope.

    The caller provides the message type and payload.
    """

    type: str
    payload: Any

    def to_dict(self) -> dict[str, Any]:
        """Convert the message to a Socket.IO payload."""

        if hasattr(
            self.payload,
            "to_dict",
        ):
            payload = self.payload.to_dict()

        else:
            payload = self.payload

        return {
            "type": self.type,
            "payload": payload,
        }
