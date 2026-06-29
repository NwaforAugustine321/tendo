"""Event system database operations and writer service.

EventStore handles:
- Event ingestion (business_events table)
- Event querying (stream queries, business-wide queries)
- Business discovery (which businesses have pending events)
- Checkpoint operations (learning_checkpoint table)
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4
from app.db.client import get_client
from app.events.models import BusinessEvent

logger = logging.getLogger(__name__)

VALID_SOURCES = {"chat", "ui", "api", "import", "system", "webhook"}


class EventStore:
    

    def __init__(self):
        self._client = get_client()

    def next_sequence_number(self, business_id: str) -> int:
        """Get the next sequence number for a business."""
        result = (
            self._client.table("business_events")
            .select("sequence_number")
            .eq("business_id", business_id)
            .order("sequence_number", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return int(result.data[0]["sequence_number"]) + 1
        return 1

    def insert_event(self, event: BusinessEvent) -> BusinessEvent:
        """Insert a business event. Returns persisted row."""
        data = {
            "id": str(event.id),
            "business_id": str(event.business_id),
            "session_id": str(event.session_id) if event.session_id else None,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "event_type": event.event_type,
            "source": event.source,
            "sequence_number": event.sequence_number,
            "payload": event.payload,
            "metadata": event.metadata,
        }
        result = self._client.table("business_events").insert(data).execute()
        if not result.data:
            raise RuntimeError("Failed to insert business event")
        return BusinessEvent(**result.data[0])

    def query_events(
        self,
        business_id: str,
        entity_type: str,
        entity_id: str,
        after_sequence: int,
        limit: int,
    ) -> list[BusinessEvent]:
        """Query events for a specific stream after a given sequence number."""
        result = (
            self._client.table("business_events")
            .select("*")
            .eq("business_id", business_id)
            .eq("entity_type", entity_type)
            .eq("entity_id", entity_id)
            .gt("sequence_number", after_sequence)
            .order("sequence_number", desc=False)
            .limit(limit)
            .execute()
        )
        return [BusinessEvent(**row) for row in (result.data or [])]

    def query_events_for_business(
        self, business_id: str, after_sequence: int, limit: int
    ) -> list[BusinessEvent]:
        """Query all events for a business regardless of entity type."""
        result = (
            self._client.table("business_events")
            .select("*")
            .eq("business_id", business_id)
            .gt("sequence_number", after_sequence)
            .order("sequence_number", desc=False)
            .limit(limit)
            .execute()
        )
        return [BusinessEvent(**row) for row in (result.data or [])]

    def query_all_events(self, after_id: int, limit: int) -> list[BusinessEvent]:
        """Query all events using offset-based pagination."""
        result = (
            self._client.table("business_events")
            .select("*")
            .order("created_at", desc=False)
            .range(after_id, after_id + limit - 1)
            .execute()
        )
        return [BusinessEvent(**row) for row in (result.data or [])]

    def query_businesses_with_pending_events(self, worker_name: str, limit: int) -> list[dict]:
        """Find businesses that have unprocessed events."""
        result = (
            self._client.table("business_events")
            .select("business_id")
            .order("created_at", desc=True)
            .execute()
        )
        if not result.data:
            return []

        seen = set()
        business_ids = []
        for row in result.data:
            bid = row["business_id"]
            if bid not in seen:
                seen.add(bid)
                business_ids.append(bid)

        ready_businesses = []
        for bid in business_ids:
            checkpoint = self.load_checkpoint(worker_name, bid)
            count_result = (
                self._client.table("business_events")
                .select("id", count="exact")
                .eq("business_id", bid)
                .gt("sequence_number", checkpoint)
                .execute()
            )
            pending = count_result.count or 0
            if pending > 0:
                ready_businesses.append({"business_id": bid, "pending_count": pending})
            if len(ready_businesses) >= limit:
                break

        ready_businesses.sort(key=lambda x: x["pending_count"], reverse=True)
        return ready_businesses

    # --- Checkpoint operations (learning_checkpoint table) ---

    def load_checkpoint(self, worker_name: str, business_id: str) -> int:
        """Load last_processed_sequence for a worker/business. Returns 0 if none."""
        result = (
            self._client.table("learning_checkpoint")
            .select("last_processed_sequence")
            .eq("worker_name", worker_name)
            .eq("business_id", business_id)
            .execute()
        )
        if result.data:
            return result.data[0]["last_processed_sequence"]
        return 0

    def save_checkpoint(self, worker_name: str, business_id: str, last_processed_sequence: int) -> None:
        """Upsert checkpoint with the last processed sequence and mark completed."""
        data = {
            "worker_name": worker_name,
            "business_id": business_id,
            "last_processed_sequence": last_processed_sequence,
            "status": "completed",
            "end_sequence": last_processed_sequence,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._client.table("learning_checkpoint").upsert(
            data, on_conflict="worker_name,business_id"
        ).execute()

    def create_or_update_job(
        self, worker_name: str, business_id: str, start_sequence: int, end_sequence: int, status: str = "pending"
    ) -> None:
        """Create or update a job entry in learning_checkpoint."""
        data = {
            "worker_name": worker_name,
            "business_id": business_id,
            "start_sequence": start_sequence,
            "end_sequence": end_sequence,
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._client.table("learning_checkpoint").upsert(
            data, on_conflict="worker_name,business_id"
        ).execute()

    def update_job_status(self, worker_name: str, business_id: str, status: str, error_message: str | None = None) -> None:
        """Update job status for a worker/business."""
        now = datetime.now(timezone.utc).isoformat()
        updates: dict = {"status": status, "updated_at": now}
        if status == "running":
            updates["started_at"] = now
        elif status in ("completed", "failed"):
            updates["completed_at"] = now
        if error_message is not None:
            updates["error_message"] = error_message
        self._client.table("learning_checkpoint").update(updates).eq(
            "worker_name", worker_name
        ).eq("business_id", business_id).execute()

    def recover_stale_jobs(self, worker_name: str) -> int:
        """Mark all running jobs as failed (recovery after crash)."""
        result = (
            self._client.table("learning_checkpoint")
            .select("*")
            .eq("worker_name", worker_name)
            .eq("status", "running")
            .execute()
        )
        stale = result.data or []
        for row in stale:
            self.update_job_status(
                worker_name=row["worker_name"],
                business_id=row["business_id"],
                status="failed",
                error_message="Recovered after worker restart",
            )
        return len(stale)


class EventWriter:
    """Centralized service for writing business events."""

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
        """Validate, sequence, and persist a business event."""
        self._validate_source(source)

        event_id = uuid4()
        sequence_number = self._next_sequence_number(business_id)

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

        return persisted_event

    def _validate_source(self, source: str) -> None:
        """Raise ValueError if source is not valid."""
        if source not in VALID_SOURCES:
            raise ValueError(
                f"Invalid source '{source}'. Must be one of: {sorted(VALID_SOURCES)}"
            )

    def _next_sequence_number(self, business_id: str) -> int:
        """Get next sequence number for the business."""
        try:
            return self._store.next_sequence_number(business_id)
        except Exception as e:
            raise RuntimeError(
                f"Failed to get next sequence number: "
                f"business_id={business_id}, error={e}"
            ) from e
