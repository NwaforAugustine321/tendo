"""Custom APScheduler job store backed by the learning_jobs table.

This jobstore can be used when persistent scheduling is needed (e.g., surviving
app restarts without re-discovering which businesses need processing).

For now the scheduler uses in-memory storage (fast startup, no UUID issues).
This module is available for future use when persistence becomes important.
"""

import logging
from datetime import datetime, timezone

from apscheduler.job import Job as APJob
from apscheduler.jobstores.base import BaseJobStore, JobLookupError, ConflictingIdError

from app.db.client import get_client

logger = logging.getLogger(__name__)

TABLE_NAME = "learning_jobs"


class LearningJobStore(BaseJobStore):
    """
    APScheduler job store that persists scheduled jobs to the learning_jobs table.

    This unifies APScheduler's job persistence with the event system's job tracking.
    The table stores both scheduler metadata (pickled job state) and event processing
    metadata (start_sequence, end_sequence, status, etc.).

    Fields used for APScheduler:
        - id: job identifier
        - worker_name: used to store pickled job state (reusing error_message field
                       would be hacky, so we add a job_state column)
        - stream_key: the business stream this job relates to
        - status: APScheduler uses 'scheduled' for pending scheduler jobs
        - started_at: next_run_time for APScheduler

    We store the serialized job in the metadata column (JSONB) under a
    'apscheduler_state' key to avoid schema changes.
    """

    def __init__(self):
        super().__init__()
        self._client = get_client()

    def start(self, scheduler, alias):
        """Called when the scheduler starts."""
        super().start(scheduler, alias)
        logger.info("LearningJobStore started")

    def shutdown(self):
        """Called when the scheduler shuts down."""
        logger.info("LearningJobStore shutting down")

    def lookup_job(self, job_id):
        """Look up a job by its ID."""
        result = (
            self._client.table(TABLE_NAME)
            .select("*")
            .eq("id", job_id)
            .eq("status", "scheduled")
            .execute()
        )
        if not result.data:
            return None
        return self._deserialize_job(result.data[0])

    def get_due_jobs(self, now):
        """Get jobs that are due to run."""
        now_str = now.isoformat()
        result = (
            self._client.table(TABLE_NAME)
            .select("*")
            .eq("status", "scheduled")
            .lte("started_at", now_str)
            .order("started_at", desc=False)
            .execute()
        )
        return self._deserialize_jobs(result.data or [])

    def get_next_run_time(self):
        """Get the earliest next run time among all scheduled jobs."""
        result = (
            self._client.table(TABLE_NAME)
            .select("started_at")
            .eq("status", "scheduled")
            .order("started_at", desc=False)
            .limit(1)
            .execute()
        )
        if result.data and result.data[0].get("started_at"):
            return datetime.fromisoformat(result.data[0]["started_at"])
        return None

    def get_all_jobs(self):
        """Get all scheduled jobs."""
        result = (
            self._client.table(TABLE_NAME)
            .select("*")
            .eq("status", "scheduled")
            .order("started_at", desc=False)
            .execute()
        )
        return self._deserialize_jobs(result.data or [])

    def add_job(self, job):
        """Add a new scheduled job. Upserts if job already exists."""
        data = self._serialize_job(job)
        self._client.table(TABLE_NAME).upsert(data, on_conflict="id").execute()

    def update_job(self, job):
        """Update an existing scheduled job."""
        data = self._serialize_job(job)
        del data["id"]  # Don't update the PK
        result = (
            self._client.table(TABLE_NAME)
            .update(data)
            .eq("id", job.id)
            .eq("status", "scheduled")
            .execute()
        )
        if not result.data:
            raise JobLookupError(job.id)

    def remove_job(self, job_id):
        """Remove a scheduled job (mark as completed rather than delete)."""
        result = (
            self._client.table(TABLE_NAME)
            .update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", job_id)
            .eq("status", "scheduled")
            .execute()
        )
        if not result.data:
            raise JobLookupError(job_id)

    def remove_all_jobs(self):
        """Remove all scheduled jobs."""
        self._client.table(TABLE_NAME).update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("status", "scheduled").execute()

    def _serialize_job(self, job: APJob) -> dict:
        """Convert an APScheduler Job to a row dict for learning_jobs."""
        import pickle
        job_state = pickle.dumps(job.__getstate__(), protocol=pickle.HIGHEST_PROTOCOL)
        next_run = job.next_run_time.isoformat() if job.next_run_time else None

        return {
            "id": job.id,
            "worker_name": "apscheduler",
            "stream_key": getattr(job, "name", job.id),
            "start_sequence": 0,
            "end_sequence": 0,
            "status": "scheduled",
            "started_at": next_run,
            "error_message": job_state.hex(),
        }

    def _deserialize_job(self, row: dict) -> APJob | None:
        """Reconstruct an APScheduler Job from a stored row."""
        import pickle
        try:
            job_state_hex = row.get("error_message", "")
            if not job_state_hex:
                return None
            job_state = pickle.loads(bytes.fromhex(job_state_hex))
            job = APJob.__new__(APJob)
            job.__setstate__(job_state)
            job._scheduler = self._scheduler
            job._jobstore_alias = self._alias
            return job
        except Exception as e:
            logger.warning(f"Failed to deserialize job {row.get('id')}: {e}")
            return None

    def _deserialize_jobs(self, rows: list[dict]) -> list[APJob]:
        """Deserialize multiple job rows, filtering out failures."""
        jobs = []
        for row in rows:
            job = self._deserialize_job(row)
            if job:
                jobs.append(job)
        return jobs
