from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4


class EventDelivery(StrEnum):
    """
    Identifies the application layer that should receive an event.

    The actual destination/routing is determined by that layer's
    handler.
    """

    APP = "app"


@dataclass(slots=True)
class ApplicationEvent:
    """
    Event exchanged between backend processes and services.

    correlation_id:
        Internal identifier used to correlate related application
        processing. 

    delivery:
        Identifies the application consumer responsible for handling
        the event. The consumer decides what to do with the event
        and where the response should be delivered.
    """

    event: str

    data: dict[str, Any] = field(
        default_factory=dict,
    )

    id: str = field(
        default_factory=lambda: str(
            uuid4(),
        ),
    )

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )

    source: str = ""

    correlation_id: str = field(
        default_factory=lambda: str(
            uuid4(),
        ),
    )

    delivery: EventDelivery | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the event into a transport-ready dictionary."""

        return {
            "id": self.id,
            "event": self.event,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "correlation_id": self.correlation_id,
            "delivery": (
                self.delivery.value
                if self.delivery is not None
                else None
            ),
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> ApplicationEvent:
        """Create an event from a transport payload."""

        event = payload.get(
            "event",
        )

        if not isinstance(
            event,
            str,
        ) or not event:
            raise ValueError(
                "Application event is missing 'event'.",
            )

        data = payload.get(
            "data",
            {},
        )

        if not isinstance(
            data,
            dict,
        ):
            raise ValueError(
                "Application event 'data' must be a dictionary.",
            )

        timestamp = payload.get(
            "timestamp",
        )

        if timestamp:

            if not isinstance(
                timestamp,
                str,
            ):
                raise ValueError(
                    "Application event 'timestamp' "
                    "must be a string.",
                )

            timestamp = datetime.fromisoformat(
                timestamp,
            )

        else:
            timestamp = datetime.now(
                timezone.utc,
            )

        raw_delivery = payload.get(
            "delivery",
        )

        delivery: EventDelivery | None = None

        if raw_delivery:

            if not isinstance(
                raw_delivery,
                str,
            ):
                raise ValueError(
                    "Application event 'delivery' "
                    "must be a string.",
                )

            try:
                delivery = EventDelivery(
                    raw_delivery,
                )

            except ValueError as exc:
                raise ValueError(
                    f"Unsupported application event "
                    f"delivery: {raw_delivery!r}.",
                ) from exc

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
            delivery=delivery,
        )
