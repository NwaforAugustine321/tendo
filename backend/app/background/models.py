from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    DEAD = "dead"


@dataclass(slots=True)
class JobContext:
    """
    Runtime context provided to a background worker.

    This contains execution information only.
    Domain-specific data belongs in payload.
    """

    job_id: str
    job_type: str
    payload: dict[str, Any] = field(default_factory=dict)

    attempt: int = 0
    max_attempts: int = 3

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )


@dataclass(slots=True)
class JobResult:
    """
    Result returned by a background worker.
    """

    success: bool

    result: Any = None

    error: str | None = None

    retryable: bool = False

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )


@dataclass(slots=True)
class JobRecord:
    """
    Persistent representation of a background job.

    This model intentionally contains no domain-specific fields.
    """

    id: str
    job_type: str
    status: JobStatus = JobStatus.PENDING

    payload: dict[str, Any] = field(
        default_factory=dict,
    )

    attempt: int = 0
    max_attempts: int = 3

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    scheduled_at: datetime | None = None

    started_at: datetime | None = None

    completed_at: datetime | None = None

    next_retry_at: datetime | None = None

    heartbeat_at: datetime | None = None

    worker_id: str | None = None

    error: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )