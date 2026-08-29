from dataclasses import dataclass
from typing import Literal


class ConfigurationError(Exception):
    """Raised when required configuration is missing."""

    pass


@dataclass
class NormalizedMessage:
    sender: str
    message_id: str
    timestamp: int
    message_type: Literal["text", "audio", "image", "document"]
    body: str | None = None
    media_id: str | None = None
    media_url: str | None = None
    mime_type: str | None = None
    filename: str | None = None

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "message_type": self.message_type,
            "body": self.body,
            "media_id": self.media_id,
            "mime_type": self.mime_type,
            "filename": self.filename,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NormalizedMessage":
        return cls(
            sender=data["sender"],
            message_id=data["message_id"],
            timestamp=data["timestamp"],
            message_type=data["message_type"],
            body=data.get("body"),
            media_id=data.get("media_id"),
            mime_type=data.get("mime_type"),
            filename=data.get("filename"),
        )
