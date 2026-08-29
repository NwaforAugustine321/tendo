from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.db.client import get_client

from .models import (
    JobRecord,
    JobStatus,
)


logger = logging.getLogger(__name__)


class JobStoreError(Exception):
    """Base exception for background job store errors."""


class JobNotFoundError(JobStoreError):
    """Raised when a background job cannot be found."""


class JobClaimError(JobStoreError):
    """Raised when a background job cannot be claimed."""


class JobStateError(JobStoreError):
    """Raised when an invalid job state transition is requested."""


class BackgroundJobStore:
    """
    Persistent repository for background jobs.

    This class owns:

    - job persistence
    - job lookup
    - job claiming
    - status transitions
    - retry scheduling
    - heartbeat updates
    - stale-job recovery

    """

    TABLE_NAME = "background_jobs"

    def __init__(
        self,
        *,
        client: Any | None = None,
    ) -> None:
        self._client = (
            client
            if client is not None
            else get_client()
        )

    #
    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    #

    async def create(
        self,
        job: JobRecord,
    ) -> JobRecord:
        """
        Persist a new background job.

        New jobs must start in PENDING state.
        """

        if job.status != JobStatus.PENDING:
            raise JobStateError(
                "New background jobs must start "
                "with status 'pending'.",
            )

        data = self._serialize_job(
            job,
        )

        try:
            response = (
                self._client
                .table(self.TABLE_NAME)
                .insert(data)
                .execute()
            )

        except Exception as exc:
            logger.exception(
                "[JobStore] Failed to create job: "
                "job_id=%s job_type=%s",
                job.id,
                job.job_type,
            )
            raise JobStoreError(
                f"Failed to create job '{job.id}'.",
            ) from exc

        if not response.data:
            raise JobStoreError(
                f"Job '{job.id}' was not created.",
            )

        return self._deserialize_job(
            response.data[0],
        )

    #
    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------
    #

    async def get(
        self,
        job_id: str,
    ) -> JobRecord | None:
        """
        Retrieve a background job by ID.
        """

        try:
            response = (
                self._client
                .table(self.TABLE_NAME)
                .select("*")
                .eq("id", job_id)
                .limit(1)
                .execute()
            )

        except Exception as exc:
            logger.exception(
                "[JobStore] Failed to retrieve job: "
                "job_id=%s",
                job_id,
            )
            raise JobStoreError(
                f"Failed to retrieve job '{job_id}'.",
            ) from exc

        if not response.data:
            return None

        return self._deserialize_job(
            response.data[0],
        )

    async def require(
        self,
        job_id: str,
    ) -> JobRecord:
        """
        Retrieve a job or raise JobNotFoundError.
        """

        job = await self.get(
            job_id,
        )

        if job is None:
            raise JobNotFoundError(
                f"Background job '{job_id}' was not found.",
            )

        return job

    #
    # ------------------------------------------------------------------
    # Pending jobs
    # ------------------------------------------------------------------
    #

    async def get_pending(
        self,
        *,
        limit: int = 100,
        now: datetime | None = None,
    ) -> list[JobRecord]:
        """
        Return jobs that are ready to be processed.

        This method only discovers work.

        It does NOT claim the jobs.

        Claiming must happen through `claim()`.
        """

        if limit <= 0:
            return []

        current_time = (
            now
            if now is not None
            else self._utcnow()
        )

        response = (
            self._client
            .table(self.TABLE_NAME)
            .select("*")
            .eq(
                "status",
                JobStatus.PENDING.value,
            )
            .or_(
                f"scheduled_at.is.null,"
                f"scheduled_at.lte.{current_time.isoformat()}",
            )
            .order(
                "scheduled_at",
                desc=False,
            )
            .limit(limit)
            .execute()
        )

        return [
            self._deserialize_job(row)
            for row in (response.data or [])
        ]

    #
    # ------------------------------------------------------------------
    # Claim
    # ------------------------------------------------------------------
    #

    async def claim(
        self,
        *,
        job_id: str,
        worker_id: str,
        lease_seconds: int = 300,
    ) -> JobRecord:
        """
        Atomically claim a pending/retryable job.

        The actual atomic operation should be implemented by the
        database RPC `claim_background_job`.

        This prevents two background workers from processing the
        same job simultaneously.
        """

        if not worker_id:
            raise ValueError(
                "worker_id is required when claiming a job.",
            )

        if lease_seconds <= 0:
            raise ValueError(
                "lease_seconds must be greater than zero.",
            )

        try:
            response = self._client.rpc(
                "claim_background_job",
                {
                    "p_job_id": job_id,
                    "p_worker_id": worker_id,
                    "p_lease_seconds": lease_seconds,
                },
            ).execute()

        except Exception as exc:
            logger.exception(
                "[JobStore] Failed to claim job: "
                "job_id=%s worker_id=%s",
                job_id,
                worker_id,
            )
            raise JobClaimError(
                f"Failed to claim job '{job_id}'.",
            ) from exc

        if not response.data:
            raise JobClaimError(
                f"Job '{job_id}' could not be claimed. "
                "It may already be claimed, completed, "
                "cancelled, or unavailable.",
            )

        row = (
            response.data[0]
            if isinstance(
                response.data,
                list,
            )
            else response.data
        )

        return self._deserialize_job(
            row,
        )

    #
    # ------------------------------------------------------------------
    # Running
    # ------------------------------------------------------------------
    #

    async def mark_running(
        self,
        *,
        job_id: str,
        worker_id: str,
    ) -> JobRecord:
        """
        Move a claimed job into RUNNING state.
        """

        now = self._utcnow()

        response = (
            self._client
            .table(self.TABLE_NAME)
            .update(
                {
                    "status": JobStatus.RUNNING.value,
                    "started_at": now.isoformat(),
                    "heartbeat_at": now.isoformat(),
                },
            )
            .eq("id", job_id)
            .eq(
                "status",
                JobStatus.CLAIMED.value,
            )
            .eq(
                "worker_id",
                worker_id,
            )
            .execute()
        )

        if not response.data:
            raise JobStateError(
                f"Job '{job_id}' could not be "
                "moved to running state.",
            )

        return self._deserialize_job(
            response.data[0],
        )

    #
    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------
    #

    async def heartbeat(
        self,
        *,
        job_id: str,
        worker_id: str,
    ) -> None:
        """
        Extend the worker's activity timestamp.

        The recovery process uses this timestamp to determine
        whether a running job has become stale.
        """

        now = self._utcnow()

        response = (
            self._client
            .table(self.TABLE_NAME)
            .update(
                {
                    "heartbeat_at": now.isoformat(),
                },
            )
            .eq("id", job_id)
            .eq(
                "worker_id",
                worker_id,
            )
            .in_(
                "status",
                [
                    JobStatus.CLAIMED.value,
                    JobStatus.RUNNING.value,
                ],
            )
            .execute()
        )

        if not response.data:
            logger.warning(
                "[JobStore] Heartbeat rejected: "
                "job_id=%s worker_id=%s",
                job_id,
                worker_id,
            )

    #
    # ------------------------------------------------------------------
    # Complete
    # ------------------------------------------------------------------
    #

    async def complete(
        self,
        *,
        job_id: str,
        worker_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> JobRecord:
        """
        Mark a running job as successfully completed.
        """

        now = self._utcnow()

        update: dict[str, Any] = {
            "status": JobStatus.COMPLETED.value,
            "completed_at": now.isoformat(),
            "heartbeat_at": now.isoformat(),
            "error": None,
        }

        if metadata is not None:
            update["metadata"] = metadata

        response = (
            self._client
            .table(self.TABLE_NAME)
            .update(update)
            .eq("id", job_id)
            .eq(
                "worker_id",
                worker_id,
            )
            .eq(
                "status",
                JobStatus.RUNNING.value,
            )
            .execute()
        )

        if not response.data:
            raise JobStateError(
                f"Job '{job_id}' could not be "
                "marked as completed.",
            )

        logger.info(
            "[JobStore] Job completed: "
            "job_id=%s worker_id=%s",
            job_id,
            worker_id,
        )

        return self._deserialize_job(
            response.data[0],
        )

    #
    # ------------------------------------------------------------------
    # Failure
    # ------------------------------------------------------------------
    #

    async def fail(
        self,
        *,
        job_id: str,
        worker_id: str,
        error: str,
        retry_at: datetime | None = None,
    ) -> JobRecord:
        """
        Mark a job as failed.

        If retry_at is provided, the job becomes RETRYING.
        Otherwise it becomes FAILED.
        """

        status = (
            JobStatus.RETRYING
            if retry_at is not None
            else JobStatus.FAILED
        )

        update: dict[str, Any] = {
            "status": status.value,
            "error": error,
            "heartbeat_at": self._utcnow().isoformat(),
        }

        if retry_at is not None:
            update["next_retry_at"] = (
                retry_at.isoformat()
            )

        response = (
            self._client
            .table(self.TABLE_NAME)
            .update(update)
            .eq("id", job_id)
            .eq(
                "worker_id",
                worker_id,
            )
            .in_(
                "status",
                [
                    JobStatus.CLAIMED.value,
                    JobStatus.RUNNING.value,
                ],
            )
            .execute()
        )

        if not response.data:
            raise JobStateError(
                f"Job '{job_id}' could not be "
                "marked as failed.",
            )

        logger.warning(
            "[JobStore] Job failed: "
            "job_id=%s worker_id=%s retry_at=%s",
            job_id,
            worker_id,
            retry_at,
        )

        return self._deserialize_job(
            response.data[0],
        )

    #
    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------
    #

    async def cancel(
        self,
        job_id: str,
    ) -> JobRecord:
        """
        Cancel a job that has not completed.
        """

        response = (
            self._client
            .table(self.TABLE_NAME)
            .update(
                {
                    "status": JobStatus.CANCELLED.value,
                    "completed_at": (
                        self._utcnow().isoformat()
                    ),
                },
            )
            .eq("id", job_id)
            .in_(
                "status",
                [
                    JobStatus.PENDING.value,
                    JobStatus.RETRYING.value,
                    JobStatus.CLAIMED.value,
                    JobStatus.RUNNING.value,
                ],
            )
            .execute()
        )

        if not response.data:
            raise JobStateError(
                f"Job '{job_id}' could not be cancelled.",
            )

        return self._deserialize_job(
            response.data[0],
        )

    #
    # ------------------------------------------------------------------
    # Retry
    # ------------------------------------------------------------------
    #

    async def make_retryable(
        self,
        *,
        job_id: str,
        retry_at: datetime,
        error: str | None = None,
    ) -> JobRecord:
        """
        Move a failed job back into RETRYING state.

        The retry scheduler/dispatcher can later make it eligible
        for claiming.
        """

        update: dict[str, Any] = {
            "status": JobStatus.RETRYING.value,
            "next_retry_at": retry_at.isoformat(),
        }

        if error is not None:
            update["error"] = error

        response = (
            self._client
            .table(self.TABLE_NAME)
            .update(update)
            .eq("id", job_id)
            .eq(
                "status",
                JobStatus.FAILED.value,
            )
            .execute()
        )

        if not response.data:
            raise JobStateError(
                f"Job '{job_id}' could not be made retryable.",
            )

        return self._deserialize_job(
            response.data[0],
        )

    #
    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------
    #

    async def recover_stale_jobs(
        self,
        *,
        stale_before: datetime,
        limit: int = 100,
    ) -> list[JobRecord]:
        """
        Recover jobs whose worker has stopped reporting activity.

        The actual transition is performed by a database RPC so
        multiple application instances cannot recover the same
        job simultaneously.
        """

        response = self._client.rpc(
            "recover_stale_background_jobs",
            {
                "p_stale_before": stale_before.isoformat(),
                "p_limit": limit,
            },
        ).execute()

        return [
            self._deserialize_job(row)
            for row in (response.data or [])
        ]

    #
    # ------------------------------------------------------------------
    # Retry-ready jobs
    # ------------------------------------------------------------------
    #

    async def promote_retryable_jobs(
        self,
        *,
        now: datetime | None = None,
        limit: int = 100,
    ) -> int:
        """
        Make retryable jobs available for claiming when their
        retry time has arrived.
        """

        current_time = (
            now
            if now is not None
            else self._utcnow()
        )

        response = (
            self._client
            .table(self.TABLE_NAME)
            .update(
                {
                    "status": JobStatus.PENDING.value,
                    "next_retry_at": None,
                },
            )
            .eq(
                "status",
                JobStatus.RETRYING.value,
            )
            .lte(
                "next_retry_at",
                current_time.isoformat(),
            )
            .limit(limit)
            .execute()
        )

        return len(
            response.data or [],
        )

    #
    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    #

    @staticmethod
    def _serialize_job(
        job: JobRecord,
    ) -> dict[str, Any]:
        return {
            "id": job.id,
            "job_type": job.job_type,
            "status": job.status.value,
            "payload": job.payload,
            "attempt": job.attempt,
            "max_attempts": job.max_attempts,
            "created_at": job.created_at.isoformat(),
            "scheduled_at": (
                job.scheduled_at.isoformat()
                if job.scheduled_at
                else None
            ),
            "started_at": (
                job.started_at.isoformat()
                if job.started_at
                else None
            ),
            "completed_at": (
                job.completed_at.isoformat()
                if job.completed_at
                else None
            ),
            "next_retry_at": (
                job.next_retry_at.isoformat()
                if job.next_retry_at
                else None
            ),
            "heartbeat_at": (
                job.heartbeat_at.isoformat()
                if job.heartbeat_at
                else None
            ),
            "worker_id": job.worker_id,
            "error": job.error,
            "metadata": job.metadata,
        }

    @staticmethod
    def _deserialize_job(
        row: dict[str, Any],
    ) -> JobRecord:
        return JobRecord(
            id=str(row["id"]),
            job_type=row["job_type"],
            status=JobStatus(
                row["status"],
            ),
            payload=row.get(
                "payload",
            ) or {},
            attempt=int(
                row.get(
                    "attempt",
                    0,
                ),
            ),
            max_attempts=int(
                row.get(
                    "max_attempts",
                    3,
                ),
            ),
            created_at=BackgroundJobStore._parse_datetime(
                row.get("created_at"),
            ),
            scheduled_at=BackgroundJobStore._parse_optional_datetime(
                row.get("scheduled_at"),
            ),
            started_at=BackgroundJobStore._parse_optional_datetime(
                row.get("started_at"),
            ),
            completed_at=BackgroundJobStore._parse_optional_datetime(
                row.get("completed_at"),
            ),
            next_retry_at=BackgroundJobStore._parse_optional_datetime(
                row.get("next_retry_at"),
            ),
            heartbeat_at=BackgroundJobStore._parse_optional_datetime(
                row.get("heartbeat_at"),
            ),
            worker_id=row.get(
                "worker_id",
            ),
            error=row.get(
                "error",
            ),
            metadata=row.get(
                "metadata",
            ) or {},
        )

    @staticmethod
    def _parse_datetime(
        value: Any,
    ) -> datetime:
        if isinstance(
            value,
            datetime,
        ):
            return value

        if not value:
            return datetime.now(
                timezone.utc,
            )

        return datetime.fromisoformat(
            str(value).replace(
                "Z",
                "+00:00",
            ),
        )

    @staticmethod
    def _parse_optional_datetime(
        value: Any,
    ) -> datetime | None:
        if value is None:
            return None

        return BackgroundJobStore._parse_datetime(
            value,
        )

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(
            timezone.utc,
        )
