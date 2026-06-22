"""Event worker with APScheduler-based per-business dispatcher."""

import json
import logging
from abc import ABC, abstractmethod
from enum import Enum
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

from app.config.settings import settings
from app.events.config import load_threshold_config
from app.events.models import BusinessEvent, Job, ThresholdConfig
from app.events.writer import EventStore
from app.db.client import get_client

logger = logging.getLogger(__name__)

# Scheduler singleton
_scheduler: BackgroundScheduler | None = None
_store: EventStore | None = None

# Track idle cycles per business to evict inactive ones
_idle_counts: dict[str, int] = {}


class WorkerState(str, Enum):
    """Lifecycle states for the worker state machine."""

    IDLE = "idle"
    CHECKING = "checking"
    LOADING_EVENTS = "loading_events"
    WAITING_FOR_THRESHOLD = "waiting_for_threshold"
    CREATING_JOB = "creating_job"
    COMPLETED = "completed"
    FAILED = "failed"


class StreamWorker(ABC):
    """
    Generic base class for stream-based event processing.

    Subclasses implement `process_job()` with domain-specific logic.
    """

    def __init__(
        self,
        worker_name: str,
        stream_key: str,
        config: ThresholdConfig | None = None,
    ):
        self.worker_name = worker_name
        self.stream_key = stream_key
        self.config = config or load_threshold_config()
        self.state = WorkerState.IDLE
        self._store = EventStore()

    def _transition(self, new_state: WorkerState) -> None:
        """Transition to a new state with structured logging."""
        old_state = self.state
        self.state = new_state
        logger.debug(
            "Worker state transition",
            extra={
                "worker_name": self.worker_name,
                "stream_key": self.stream_key,
                "from_state": old_state.value,
                "to_state": new_state.value,
            },
        )

    def poll(self) -> Job | None:
        """Execute one polling cycle. Returns created Job or None."""
        try:
            self._transition(WorkerState.CHECKING)
            last_sequence = self._store.load_checkpoint(self.worker_name, self.stream_key)

            self._transition(WorkerState.LOADING_EVENTS)
            events = self._load_events(last_sequence)

            if not self._evaluate_thresholds(events):
                self._transition(WorkerState.WAITING_FOR_THRESHOLD)
                self._transition(WorkerState.IDLE)
                return None

            self._transition(WorkerState.CREATING_JOB)
            batch_events = events[: self.config.max_events_per_batch]
            start_sequence = batch_events[0].sequence_number
            end_sequence = batch_events[-1].sequence_number

            job = Job(
                id=str(uuid4()),
                worker_name=self.worker_name,
                stream_key=self.stream_key,
                start_sequence=start_sequence,
                end_sequence=end_sequence,
                status="pending",
            )
            created_job = self._store.create_job(job)

            self._store.update_job_status(str(created_job.id), "running")

            try:
                self.process_job(created_job, batch_events)
            except Exception as e:
                error_msg = str(e)
                self._store.update_job_status(
                    str(created_job.id), "failed", error_message=error_msg
                )
                logger.error(
                    "Error in process_job",
                    extra={
                        "worker_name": self.worker_name,
                        "stream_key": self.stream_key,
                        "error": error_msg,
                    },
                )
                self._transition(WorkerState.FAILED)
                self._transition(WorkerState.IDLE)
                return None

            self._store.update_job_status(str(created_job.id), "completed")

            self._store.save_checkpoint(self.worker_name, self.stream_key, end_sequence)
            logger.info(
                "Checkpoint updated",
                extra={
                    "worker_name": self.worker_name,
                    "stream_key": self.stream_key,
                    "last_processed_sequence": end_sequence,
                },
            )

            self._transition(WorkerState.COMPLETED)
            self._transition(WorkerState.IDLE)
            return created_job

        except Exception as e:
            logger.error(
                "Error during poll cycle",
                extra={
                    "worker_name": self.worker_name,
                    "stream_key": self.stream_key,
                    "error": str(e),
                },
            )
            self._transition(WorkerState.FAILED)
            self._transition(WorkerState.IDLE)
            return None

    def _load_events(self, after_sequence: int) -> list[BusinessEvent]:
        """Load events for this worker's business after the checkpoint."""
        # Extract business_id from stream_key format: "{business_id}:all:events"
        business_id = self.stream_key.split(":")[0]
        return self._store.query_events_for_business(
            business_id=business_id,
            after_sequence=after_sequence,
            limit=self.config.max_batch_size,
        )

    def recover_stale_jobs(self) -> None:
        """Find running jobs for this worker and mark them as failed."""
        stale_jobs = self._store.find_stale_jobs(self.worker_name)
        for job in stale_jobs:
            self._store.update_job_status(
                str(job.id), "failed", error_message="Recovered after worker restart"
            )
            logger.info(
                "Stale job recovered",
                extra={"job_id": str(job.id), "worker_name": self.worker_name},
            )

    def _evaluate_thresholds(self, events: list[BusinessEvent]) -> bool:
        """Return True if events meet both min_event_count and min_char_count."""
        event_count = len(events)
        char_count = self._compute_char_count(events)
        meets_threshold = (
            event_count >= self.config.min_event_count
            and char_count >= self.config.min_char_count
        )
        logger.debug(
            "Threshold evaluation",
            extra={
                "worker_name": self.worker_name,
                "event_count": event_count,
                "char_count": char_count,
                "meets_threshold": meets_threshold,
            },
        )
        return meets_threshold

    def _compute_char_count(self, events: list[BusinessEvent]) -> int:
        """Sum of JSON-serialized payload lengths across all events."""
        total = 0
        for event in events:
            total += len(json.dumps(event.payload))
        return total

    @abstractmethod
    def process_job(self, job: Job, events: list[BusinessEvent]) -> None:
        """Subclass hook for domain-specific processing."""
        ...


# ---------------------------------------------------------------------------
# Concrete worker for per-business event processing
# ---------------------------------------------------------------------------


class BusinessEventWorker(StreamWorker):
    """Processes events for a single business."""

    def process_job(self, job: Job, events: list[BusinessEvent]) -> None:
        """Process a batch of business events."""
        logger.info(
            "Processing event batch",
            extra={
                "job_id": str(job.id),
                "worker_name": self.worker_name,
                "stream_key": self.stream_key,
                "event_count": len(events),
                "start_sequence": job.start_sequence,
                "end_sequence": job.end_sequence,
            },
        )


# ---------------------------------------------------------------------------
# APScheduler-based dispatcher
# ---------------------------------------------------------------------------


WORKER_NAME = "business_learning_worker"


def _process_business(business_id: str) -> None:
    """Run one poll cycle for a specific business. Called by APScheduler."""
    global _idle_counts

    stream_key = f"{business_id}:all:events"
    worker = BusinessEventWorker(
        worker_name=WORKER_NAME,
        stream_key=stream_key,
    )
    job = worker.poll()

    if job is None:
        # No work done — increment idle count
        _idle_counts[business_id] = _idle_counts.get(business_id, 0) + 1
    else:
        # Work done — reset idle count
        _idle_counts[business_id] = 0


def _dispatch() -> None:
    """
    Dispatcher job — runs on interval.
    Discovers businesses with pending events and schedules them.
    Evicts idle businesses that have no pending work.
    """
    global _scheduler, _store, _idle_counts

    if not _scheduler or not _store:
        return

    max_workers = settings.event_max_concurrent_workers
    idle_eviction = settings.event_idle_eviction_cycles

    # Find businesses with pending events (prioritized by count)
    ready_businesses = _store.query_businesses_with_pending_events(
        worker_name=WORKER_NAME,
        limit=max_workers,
    )

    # Get currently scheduled business job ids
    scheduled_jobs = {
        job.id for job in _scheduler.get_jobs()
        if job.id.startswith("biz_")
    }

    # Evict idle businesses
    for job_id in list(scheduled_jobs):
        business_id = job_id.replace("biz_", "")
        idle_count = _idle_counts.get(business_id, 0)
        if idle_count >= idle_eviction:
            _scheduler.remove_job(job_id)
            _idle_counts.pop(business_id, None)
            logger.debug(
                "Evicted idle business from scheduler",
                extra={"business_id": business_id, "idle_cycles": idle_count},
            )

    # Schedule ready businesses (up to max_workers)
    current_count = len([
        j for j in _scheduler.get_jobs() if j.id.startswith("biz_")
    ])

    for biz in ready_businesses:
        if current_count >= max_workers:
            break

        job_id = f"biz_{biz['business_id']}"
        if job_id not in scheduled_jobs:
            _scheduler.add_job(
                _process_business,
                "interval",
                seconds=settings.event_polling_interval_seconds,
                id=job_id,
                args=[biz["business_id"]],
                max_instances=1,
                replace_existing=True,
            )
            _idle_counts[biz["business_id"]] = 0
            current_count += 1
            logger.info(
                "Scheduled business for processing",
                extra={
                    "business_id": biz["business_id"],
                    "pending_count": biz["pending_count"],
                },
            )


def start_scheduler() -> None:
    """Start the APScheduler-based event processing system."""
    global _scheduler, _store

    if _scheduler and _scheduler.running:
        logger.warning("Event scheduler already running")
        return

    _store = EventStore()

    max_workers = settings.event_max_concurrent_workers
    dispatcher_interval = settings.event_dispatcher_interval

    executors = {
        "default": ProcessPoolExecutor(5),
        "threadpool": ThreadPoolExecutor(max_workers),
    }

    from app.events.scheduler_store import LearningJobStore

    jobstore = LearningJobStore()

    # Clear all stale scheduled jobs from previous runs to ensure fresh intervals
    jobstore._client = get_client()
    get_client().table("learning_jobs").delete().eq("status", "scheduled").execute()

    jobstores = {
        "default": jobstore,
    }

    _scheduler = BackgroundScheduler(executors=executors, jobstores=jobstores)

    # Recover stale jobs on startup
    worker = BusinessEventWorker(worker_name=WORKER_NAME, stream_key="startup:recovery:init")
    worker.recover_stale_jobs()

    # Add the dispatcher job (runs in threadpool — lightweight scheduling logic)
    _scheduler.add_job(
        _dispatch,
        "interval",
        seconds=dispatcher_interval,
        id="event_dispatcher",
        max_instances=1,
        executor="threadpool",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Event scheduler started",
        extra={
            "max_workers": max_workers,
            "dispatcher_interval": dispatcher_interval,
        },
    )


def stop_scheduler() -> None:
    """Shutdown the scheduler gracefully."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Event scheduler stopped")
    _scheduler = None
