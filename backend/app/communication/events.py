from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4


@dataclass(slots=True)
class ApplicationEvent:
    """Event exchanged between backend processes and services."""

    event: str

    data: dict[str, Any] = field(
        default_factory=dict,
    )

    id: str = field(
        default_factory=lambda: str(uuid4()),
    )

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    source: str = ""

    correlation_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert the event into a transport-ready dictionary."""

        return {
            "id": self.id,
            "event": self.event,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> ApplicationEvent:
        """Create an event from a transport payload."""

        event = payload.get("event")

        if not isinstance(event, str) or not event:
            raise ValueError(
                "Application event is missing 'event'."
            )

        data = payload.get("data", {})

        if not isinstance(data, dict):
            raise ValueError(
                "Application event 'data' must be a dictionary."
            )

        timestamp = payload.get("timestamp")

        if timestamp:
            if not isinstance(timestamp, str):
                raise ValueError(
                    "Application event 'timestamp' must be a string."
                )

            timestamp = datetime.fromisoformat(
                timestamp,
            )
        else:
            timestamp = datetime.now(
                timezone.utc,
            )

        return cls(
            id=payload.get(
                "id",
                str(uuid4()),
            ),
            event=event,
            data=data,
            timestamp=timestamp,
            source=payload.get(
                "source",
                "",
            ),
            correlation_id=payload.get(
                "correlation_id",
                "",
            ),
        )
