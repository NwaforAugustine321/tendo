import json
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config.settings import settings
from app.events.config import load_threshold_config
from app.events.models import BusinessEvent, Job
from app.events.writer import EventStore
from app.scheduler.worker import BaseWorker

logger = logging.getLogger(__name__)

WORKER_NAME = "business_learning_worker"


class BusinessEventWorker(BaseWorker):

    def __init__(self):
        super().__init__(name=WORKER_NAME)
        self._store = EventStore()
        self._config = load_threshold_config()

    async def process(self, context: dict) -> Job | None:
        """Poll for events for the given business and run BLA."""
        business_id = context["business_id"]

        last_sequence = self._store.load_checkpoint(self.name, business_id)

        events = self._store.query_events_for_business(
            business_id=business_id,
            after_sequence=last_sequence,
            limit=self._config.max_batch_size,
        )

        if not self._meets_threshold(events):
            return None

        batch = events[: self._config.max_events_per_batch]
        start_seq = batch[0].sequence_number
        end_seq = batch[-1].sequence_number

        # Track in checkpoint
        self._store.create_or_update_job(
            self.name, business_id, start_seq, end_seq, "running"
        )

        job = Job(
            worker_name=self.name,
            business_id=business_id,
            start_sequence=start_seq,
            end_sequence=end_seq,
            status="running",
        )

        try:
            from app.business_knowledge.agent import process_events
            await process_events(job, batch)
        except Exception as e:
            self._store.update_job_status(
                self.name, business_id, "failed", error_message=str(e)
            )
            raise

        self._store.save_checkpoint(self.name, business_id, end_seq)
        return job

    def recover_stale_jobs(self) -> None:
        """Mark any running jobs from previous crashes as failed."""
        self._store.recover_stale_jobs(self.name)

    def _meets_threshold(self, events: list[BusinessEvent]) -> bool:
        """Check if enough events have accumulated."""
        if len(events) < self._config.min_event_count:
            return False
        char_count = sum(len(json.dumps(e.payload)) for e in events)
        return char_count >= self._config.min_char_count


_worker = BusinessEventWorker()

async def _bla_dispatch() -> None:
    """Dispatcher: finds businesses with pending events and processes them directly."""
    store = EventStore()

    ready_businesses = store.query_businesses_with_pending_events(
        worker_name=WORKER_NAME,
        limit=settings.event_max_concurrent_workers,
    )

    for biz in ready_businesses:
        await _worker.run(context={"business_id": biz["business_id"]})


def register_event_jobs(scheduler: AsyncIOScheduler) -> None:
    """Register the business event dispatcher job on the scheduler."""
    _worker.recover_stale_jobs()

    dispatcher_interval = settings.event_dispatcher_interval
    scheduler.add_job(
        _bla_dispatch,
        "interval",
        seconds=dispatcher_interval,
        id="event_dispatcher",
        max_instances=1,
        replace_existing=True,
    )
