"""Business Event System — public API."""

from app.events.config import load_threshold_config, load_scheduler_config
from app.events.models import (
    BusinessEvent,
    Checkpoint,
    EventSource,
    EventWriteRequest,
    Job,
    JobStatus,
    ThresholdConfig,
)
from app.events.writer import EventStore, EventWriter


def __getattr__(name: str):
    """Lazy import worker symbols to avoid pulling in apscheduler at import time."""
    _worker_symbols = {
        "BusinessEventWorker",
        "StreamWorker",
        "WorkerState",
        "start_scheduler",
        "stop_scheduler",
    }
    if name in _worker_symbols:
        from app.events import worker
        return getattr(worker, name)
    raise AttributeError(f"module 'app.events' has no attribute {name!r}")


__all__ = [
    "BusinessEvent",
    "BusinessEventWorker",
    "Checkpoint",
    "EventSource",
    "EventStore",
    "EventWriteRequest",
    "EventWriter",
    "Job",
    "JobStatus",
    "StreamWorker",
    "ThresholdConfig",
    "WorkerState",
    "load_scheduler_config",
    "load_threshold_config",
    "start_scheduler",
    "stop_scheduler",
]
