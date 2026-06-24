import json
import logging
from abc import ABC, abstractmethod
from enum import Enum
from uuid import uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config.settings import settings
from app.events.config import load_threshold_config
from app.events.models import BusinessEvent, Job, ThresholdConfig
from app.events.writer import EventStore
from app.db.client import get_client

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_store: EventStore | None = None
_idle_counts: dict[str, int] = {}


class WorkerState(str, Enum):
    IDLE = "idle"
    CHECKING = "checking"
    LOADING_EVENTS = "loading_events"
    WAITING_FOR_THRESHOLD = "waiting_for_threshold"
    CREATING_JOB = "creating_job"
    COMPLETED = "completed"
    FAILED = "failed"


class StreamWorker(ABC):
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
        self.state = new_state

    async def poll(self) -> Job | None:
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

            existing_job = self._store.find_existing_job(self.worker_name, self.stream_key)
            if existing_job:
                created_job = existing_job
                self._store.update_job_status(str(created_job.id), "pending")
            else:
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
                await self.process_job(created_job, batch_events)
            except Exception as e:
                error_msg = str(e)
                self._store.update_job_status(
                    str(created_job.id), "failed", error_message=error_msg
                )
                logger.error(
                    f"Error in process_job: {error_msg}",
                    exc_info=True,
                    extra={"worker_name": self.worker_name, "stream_key": self.stream_key},
                )
                self._transition(WorkerState.FAILED)
                self._transition(WorkerState.IDLE)
                return None

            self._store.update_job_status(str(created_job.id), "completed")
            self._store.save_checkpoint(self.worker_name, self.stream_key, end_sequence)

            self._transition(WorkerState.COMPLETED)
            self._transition(WorkerState.IDLE)
            return created_job

        except Exception as e:
            logger.error(
                "Error during poll cycle",
                extra={"worker_name": self.worker_name, "stream_key": self.stream_key, "error": str(e)},
            )
            self._transition(WorkerState.FAILED)
            self._transition(WorkerState.IDLE)
            return None

    def _load_events(self, after_sequence: int) -> list[BusinessEvent]:
        business_id = self.stream_key.split(":")[0]
        return self._store.query_events_for_business(
            business_id=business_id,
            after_sequence=after_sequence,
            limit=self.config.max_batch_size,
        )

    def recover_stale_jobs(self) -> None:
        stale_jobs = self._store.find_stale_jobs(self.worker_name)
        for job in stale_jobs:
            self._store.update_job_status(
                str(job.id), "failed", error_message="Recovered after worker restart"
            )

    def _evaluate_thresholds(self, events: list[BusinessEvent]) -> bool:
        event_count = len(events)
        char_count = self._compute_char_count(events)
        return (
            event_count >= self.config.min_event_count
            and char_count >= self.config.min_char_count
        )

    def _compute_char_count(self, events: list[BusinessEvent]) -> int:
        total = 0
        for event in events:
            total += len(json.dumps(event.payload))
        return total

    @abstractmethod
    async def process_job(self, job: Job, events: list[BusinessEvent]) -> None:
        ...


class BusinessEventWorker(StreamWorker):
    async def process_job(self, job: Job, events: list[BusinessEvent]) -> None:
        from app.intelligence.agent import process_events
        await process_events(job, events)


WORKER_NAME = "business_learning_worker"


async def _process_business(business_id: str) -> None:
    global _idle_counts

    stream_key = f"{business_id}:all:events"
    worker = BusinessEventWorker(
        worker_name=WORKER_NAME,
        stream_key=stream_key,
    )
    job = await worker.poll()

    if job is None:
        _idle_counts[business_id] = _idle_counts.get(business_id, 0) + 1
    else:
        _idle_counts[business_id] = 0


async def _dispatch() -> None:
    global _scheduler, _store, _idle_counts

    if not _scheduler or not _store:
        return

    max_workers = settings.event_max_concurrent_workers
    idle_eviction = settings.event_idle_eviction_cycles

    ready_businesses = _store.query_businesses_with_pending_events(
        worker_name=WORKER_NAME,
        limit=max_workers,
    )

    scheduled_jobs = {
        job.id for job in _scheduler.get_jobs()
        if job.id.startswith("biz_")
    }

    for job_id in list(scheduled_jobs):
        business_id = job_id.replace("biz_", "")
        idle_count = _idle_counts.get(business_id, 0)
        if idle_count >= idle_eviction:
            _scheduler.remove_job(job_id)
            _idle_counts.pop(business_id, None)

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


def start_scheduler() -> None:
    global _scheduler, _store

    if _scheduler and _scheduler.running:
        logger.warning("Event scheduler already running")
        return

    _store = EventStore()

    max_workers = settings.event_max_concurrent_workers
    dispatcher_interval = settings.event_dispatcher_interval

    from app.events.scheduler_store import LearningJobStore

    jobstore = LearningJobStore()
    jobstore._client = get_client()
    get_client().table("learning_jobs").delete().eq("status", "scheduled").execute()

    _scheduler = AsyncIOScheduler(
        jobstores={"default": jobstore},
    )

    worker = BusinessEventWorker(worker_name=WORKER_NAME, stream_key="startup:recovery:init")
    worker.recover_stale_jobs()

    _scheduler.add_job(
        _dispatch,
        "interval",
        seconds=dispatcher_interval,
        id="event_dispatcher",
        max_instances=1,
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Event scheduler started",
        extra={"max_workers": max_workers, "dispatcher_interval": dispatcher_interval},
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Event scheduler stopped")
    _scheduler = None
