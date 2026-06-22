"""Centralized service for writing business events to the event store."""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.events.models import BusinessEvent
from app.events.store import EventStore

logger = logging.getLogger(__name__)

VALID_SOURCES = {"chat", "ui", "api", "import", "system", "webhook"}


class EventWriter:
    """Centralized service for writing business events to the event store."""

    def __init__(self):
        self._store = EventStore()

    def write(
        self,
        business_id: str,
        entity_type: str,
        entity_id: str,
        event_type: str,
        source: str,
        payload: dict,
        session_id: str | None = None,
        metadata: dict | None = None,
    ) -> BusinessEvent:
        """
        Validate, sequence, and persist a business event.

        Raises:
            ValueError: If source is not a valid EventSource.
            RuntimeError: If the database insert fails.

        Returns:
            The fully persisted BusinessEvent with id, sequence_number, and created_at.
        """
        self._validate_source(source)

        event_id = uuid4()
        sequence_number = self._next_sequence_number(business_id, entity_type, entity_id)

        event = BusinessEvent(
            id=event_id,
            business_id=business_id,
            session_id=session_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            source=source,
            sequence_number=sequence_number,
            payload=payload,
            metadata=metadata if metadata is not None else {},
            created_at=datetime.now(timezone.utc),
        )

        try:
            persisted_event = self._store.insert_event(event)
        except Exception as e:
            raise RuntimeError(
                f"Failed to persist event: event_type={event_type}, "
                f"entity_type={entity_type}, entity_id={entity_id}, "
                f"error={e}"
            ) from e

        logger.info(
            "Event persisted successfully",
            extra={
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "sequence_number": persisted_event.sequence_number,
            },
        )

        return persisted_event

    def _validate_source(self, source: str) -> None:
        """Raise ValueError if source is not in VALID_SOURCES."""
        if source not in VALID_SOURCES:
            raise ValueError(
                f"Invalid source '{source}'. Must be one of: {sorted(VALID_SOURCES)}"
            )

    def _next_sequence_number(
        self, business_id: str, entity_type: str, entity_id: str
    ) -> int:
        """
        Compute next sequence number for the stream via the EventStore.

        Delegates to EventStore.next_sequence_number() which queries the
        max sequence for the stream and returns max + 1.
        """
        try:
            return self._store.next_sequence_number(business_id, entity_type, entity_id)
        except Exception as e:
            raise RuntimeError(
                f"Failed to get next sequence number: "
                f"business_id={business_id}, entity_type={entity_type}, "
                f"entity_id={entity_id}, error={e}"
            ) from e
