"""APScheduler job store
"""

import logging
import pickle
from datetime import datetime, timezone
from apscheduler.job import Job as APJob
from apscheduler.jobstores.base import BaseJobStore, JobLookupError
from app.db.client import get_client

logger = logging.getLogger(__name__)

TABLE_NAME = "scheduler_jobs"


class SchedulerJobStore(BaseJobStore):
    """APScheduler job store that persists all scheduled jobs to scheduler_jobs table."""

    def __init__(self):
        super().__init__()
        self._client = get_client()

    def start(self, scheduler, alias):
        """Called when the scheduler starts."""
        super().start(scheduler, alias)
        logger.info("SchedulerJobStore started")

    def shutdown(self):
        """Called when the scheduler shuts down."""
        logger.info("SchedulerJobStore shutting down")

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
            .lte("next_run_at", now_str)
            .order("next_run_at", desc=False)
            .execute()
        )
        return self._deserialize_jobs(result.data or [])

    def get_next_run_time(self):
        """Get the earliest next run time among all scheduled jobs."""
        result = (
            self._client.table(TABLE_NAME)
            .select("next_run_at")
            .eq("status", "scheduled")
            .order("next_run_at", desc=False)
            .limit(1)
            .execute()
        )
        if result.data and result.data[0].get("next_run_at"):
            return datetime.fromisoformat(result.data[0]["next_run_at"])
        return None

    def get_all_jobs(self):
        """Get all scheduled jobs."""
        result = (
            self._client.table(TABLE_NAME)
            .select("*")
            .eq("status", "scheduled")
            .order("next_run_at", desc=False)
            .execute()
        )
        return self._deserialize_jobs(result.data or [])

    def add_job(self, job):
        """Add a new scheduled job."""
        data = self._serialize_job(job)
        self._client.table(TABLE_NAME).upsert(data, on_conflict="id").execute()

    def update_job(self, job):
        """Update an existing scheduled job."""
        data = self._serialize_job(job)
        del data["id"]
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
        """Remove a scheduled job."""
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
        """Serialize an APScheduler Job to a row."""
        job_state = pickle.dumps(job.__getstate__(), protocol=pickle.HIGHEST_PROTOCOL)
        next_run = job.next_run_time.isoformat() if job.next_run_time else None
        return {
            "id": job.id,
            "job_name": getattr(job, "name", job.id),
            "status": "scheduled",
            "next_run_at": next_run,
            "job_state": job_state.hex(),
        }

    def _deserialize_job(self, row: dict) -> APJob | None:
        """Reconstruct an APScheduler Job from a stored row."""
        try:
            job_state_hex = row.get("job_state", "")
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
        """Deserialize multiple job rows."""
        jobs = []
        for row in rows:
            job = self._deserialize_job(row)
            if job:
                jobs.append(job)
        return jobs


def clear_scheduled_jobs() -> None:
    """Clear all scheduled jobs on startup (fresh start)."""
    client = get_client()
    client.table(TABLE_NAME).delete().eq("status", "scheduled").execute()
