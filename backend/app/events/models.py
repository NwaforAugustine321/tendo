

from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

EventSource = Literal["chat", "ui", "api", "import", "system", "webhook"]
JobStatus = Literal["pending", "running", "completed", "failed", "scheduled"]


class BusinessEvent(BaseModel):

    id: UUID
    business_id: UUID
    session_id: UUID | None = None
    entity_type: str
    entity_id: str
    event_type: str
    source: EventSource
    sequence_number: int
    payload: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime


class EventWriteRequest(BaseModel):
    """Input model for the EventWriter.write() method."""

    business_id: UUID
    entity_type: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    source: EventSource
    payload: dict = Field(default_factory=dict)
    session_id: UUID | None = None
    metadata: dict = Field(default_factory=dict)


class Checkpoint(BaseModel):
    """Worker checkpoint tracking last processed sequence."""
    worker_name: str
    business_id: str
    last_processed_sequence: int = 0
    updated_at: datetime


class Job(BaseModel):
    """A unit of work created by a StreamWorker."""

    id: str = ""  # DB-generated UUID
    worker_name: str
    business_id: str
    start_sequence: int = 0
    end_sequence: int = 0
    status: JobStatus = "pending"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class ThresholdConfig(BaseModel):
    """Configurable thresholds for StreamWorker job creation."""

    min_event_count: int
    min_char_count: int
    max_events_per_batch: int
    polling_interval_seconds: int
    max_batch_size: int
