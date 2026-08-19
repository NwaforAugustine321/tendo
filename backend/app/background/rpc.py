from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.db.client import get_client

from .interfaces import BackgroundJobRPC


logger = logging.getLogger(__name__)


TABLE_NAME = "background_jobs"

DEFAULT_MAX_ATTEMPTS = 8

MAX_ERROR_LENGTH = 10_000


class DatabaseBackgroundJobRPC(BackgroundJobRPC):
    """
    PostgreSQL-backed implementation of BackgroundJobRPC.

    This class is responsible only for durable background-job
    coordination.

    PostgreSQL owns:

        - job persistence
        - atomic job claiming
        - attempt counting
        - retry decisions
        - retry backoff
        - scheduled execution
        - stale-job recovery
        - heartbeat ownership

    This class does NOT:

        - execute jobs
        - resolve workers
        - schedule application callbacks
        - calculate retry delays
        - sleep between retries

    Execution flow:

        APScheduler
            ↓
        BackgroundDispatcher
            ↓
        BackgroundRunner
            ↓
        BackgroundWorker

    This RPC layer only communicates with the durable job store.
    """

    def __init__(self) -> None:
        self._client = get_client()

    # ==================================================================
    # ENQUEUE
    # ==================================================================

    async def enqueue(
        self,
        *,
        job_type: str,
        user_id: str | None = None,
        payload: dict[str, Any] | None = None,
        run_at: str | None = None,
        priority: int = 0,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> str:
        """
        Create a durable background job.

        Newly created jobs start as:

            pending

        A job becomes eligible for claiming when:

            scheduled_at <= now()

        Retry scheduling is handled entirely by PostgreSQL.
        """

        job_type = self._validate_job_type(
            job_type,
        )

        if user_id is not None:
            if not isinstance(
                user_id,
                str,
            ):
                raise TypeError(
                    "user_id must be a string or None.",
                )

            user_id = user_id.strip()

            if not user_id:
                raise ValueError(
                    "user_id cannot be empty.",
                )

        if payload is not None and not isinstance(
            payload,
            dict,
        ):
            raise TypeError(
                "payload must be a dictionary.",
            )

        if not isinstance(
            priority,
            int,
        ):
            raise TypeError(
                "priority must be an integer.",
            )

        if priority < 0:
            raise ValueError(
                "priority must be greater than or equal to 0.",
            )

        if not isinstance(
            max_attempts,
            int,
        ):
            raise TypeError(
                "max_attempts must be an integer.",
            )

        if max_attempts < 1:
            raise ValueError(
                "max_attempts must be greater than or equal to 1.",
            )

        scheduled_at = self._normalize_run_at(
            run_at,
        )

        job_id = str(
            uuid4(),
        )

        now = self._utc_now()

        if scheduled_at is None:
            scheduled_at = now

        data = {
            "id": job_id,
            "job_type": job_type,
            "user_id": user_id,
            "payload": payload or {},
            "status": "pending",
            "priority": priority,
            "attempts": 0,
            "max_attempts": max_attempts,
            "scheduled_at": scheduled_at,
            "created_at": now,
            "updated_at": now,
        }

        try:
            response = (
                self._client
                .table(TABLE_NAME)
                .insert(data)
                .execute()
            )

        except Exception:
            logger.exception(
                "[BackgroundJobRPC] "
                "Failed to enqueue job: "
                "job_id=%s "
                "job_type=%s "
                "user_id=%s",
                job_id,
                job_type,
                user_id,
            )
            raise

        if not response.data:
            raise RuntimeError(
                "Failed to enqueue background job: "
                f"job_type={job_type}",
            )

        logger.info(
            "[BackgroundJobRPC] "
            "Job enqueued: "
            "job_id=%s "
            "job_type=%s "
            "user_id=%s "
            "scheduled_at=%s",
            job_id,
            job_type,
            user_id,
            scheduled_at,
        )

        return job_id

    # ==================================================================
    # CLAIM
    # ==================================================================

    async def claim(
        self,
        *,
        worker_name: str,
        limit: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Atomically claim pending jobs.

        The actual concurrency guarantee belongs to the PostgreSQL
        function:

            claim_background_jobs

        That function should use row-level locking such as:

            FOR UPDATE SKIP LOCKED

        Multiple application instances can therefore safely
        call claim() concurrently.
        """

        worker_name = self._validate_worker_name(
            worker_name,
        )

        if not isinstance(
            limit,
            int,
        ):
            raise TypeError(
                "limit must be an integer.",
            )

        if limit < 1:
            raise ValueError(
                "limit must be greater than or equal to 1.",
            )

        now = self._utc_now()

        try:
            response = self._client.rpc(
                "claim_background_jobs",
                {
                    "p_worker_name": worker_name,
                    "p_limit": limit,
                    "p_now": now,
                },
            ).execute()

        except Exception:
            logger.exception(
                "[BackgroundJobRPC] "
                "Failed to claim jobs: "
                "worker=%s "
                "limit=%s",
                worker_name,
                limit,
            )
            raise

        jobs = response.data or []

        if not isinstance(
            jobs,
            list,
        ):
            raise TypeError(
                "claim_background_jobs returned "
                "an invalid response.",
            )

        if jobs:
            logger.debug(
                "[BackgroundJobRPC] "
                "Jobs claimed: "
                "worker=%s "
                "count=%s",
                worker_name,
                len(jobs),
            )

        return jobs

    # ==================================================================
    # COMPLETE
    # ==================================================================

    async def complete(
        self,
        *,
        job_id: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        """
        Mark a running job as completed.

        Valid transition:

            running -> completed

        PostgreSQL is responsible for validating that the
        transition is still legal.
        """

        job_id = self._validate_job_id(
            job_id,
        )

        if result is not None and not isinstance(
            result,
            dict,
        ):
            raise TypeError(
                "result must be a dictionary.",
            )

        try:
            response = self._client.rpc(
                "complete_background_job",
                {
                    "p_job_id": job_id,
                    "p_result": result or {},
                },
            ).execute()

        except Exception:
            logger.exception(
                "[BackgroundJobRPC] "
                "Failed to complete job: "
                "job_id=%s",
                job_id,
            )
            raise

        if not response.data:
            raise RuntimeError(
                "Background job could not be completed: "
                f"{job_id}. "
                "The job may no longer be running.",
            )

        logger.debug(
            "[BackgroundJobRPC] "
            "Job completed: "
            "job_id=%s",
            job_id,
        )

    # ==================================================================
    # FAIL
    # ==================================================================

    async def fail(
        self,
        *,
        job_id: str,
        error: str,
        retry: bool = True,
    ) -> None:
        """
        Fail a running job or request a retry.

        PostgreSQL decides the resulting state.

        If retry is requested and attempts remain:

            running
                ↓
            pending
                ↓
            database retry backoff
                ↓
            running

        If attempts are exhausted:

            running
                ↓
            failed

        The application never calculates or sleeps for
        retry backoff.
        """

        job_id = self._validate_job_id(
            job_id,
        )

        if not isinstance(
            error,
            str,
        ):
            raise TypeError(
                "error must be a string.",
            )

        if not isinstance(
            retry,
            bool,
        ):
            raise TypeError(
                "retry must be a boolean.",
            )

        error_message = (
            error.strip()
            or "Background job failed."
        )

        error_message = error_message[
            :MAX_ERROR_LENGTH
        ]

        try:
            response = self._client.rpc(
                "fail_background_job",
                {
                    "p_job_id": job_id,
                    "p_error": error_message,
                    "p_retry": retry,
                },
            ).execute()

        except Exception:
            logger.exception(
                "[BackgroundJobRPC] "
                "Failed to update job failure: "
                "job_id=%s",
                job_id,
            )
            raise

        if not response.data:
            raise RuntimeError(
                "Background job could not be marked as failed: "
                f"{job_id}. "
                "The job may no longer be running.",
            )

        updated_job = response.data[0]

        logger.warning(
            "[BackgroundJobRPC] "
            "Job failure recorded: "
            "job_id=%s "
            "status=%s "
            "attempts=%s "
            "scheduled_at=%s",
            job_id,
            updated_job.get("status"),
            updated_job.get("attempts"),
            updated_job.get("scheduled_at"),
        )

    # ==================================================================
    # HEARTBEAT
    # ==================================================================

    async def heartbeat(
        self,
        *,
        job_id: str,
        worker_name: str,
    ) -> None:
        """
        Update the heartbeat of a running job.

        PostgreSQL verifies:

            - job_id
            - worker_name
            - status = running

        This prevents one worker from updating another
        worker's claimed job.
        """

        job_id = self._validate_job_id(
            job_id,
        )

        worker_name = self._validate_worker_name(
            worker_name,
        )

        try:
            response = self._client.rpc(
                "heartbeat_background_job",
                {
                    "p_job_id": job_id,
                    "p_worker_name": worker_name,
                },
            ).execute()

        except Exception:
            logger.exception(
                "[BackgroundJobRPC] "
                "Heartbeat failed: "
                "job_id=%s "
                "worker=%s",
                job_id,
                worker_name,
            )
            raise

        if not response.data:
            raise RuntimeError(
                "Background job heartbeat rejected: "
                f"job_id={job_id}, "
                f"worker={worker_name}. "
                "The job may no longer be running or "
                "may have been claimed by another worker.",
            )

        logger.debug(
            "[BackgroundJobRPC] "
            "Heartbeat updated: "
            "job_id=%s "
            "worker=%s",
            job_id,
            worker_name,
        )

    # ==================================================================
    # RECOVER STALE
    # ==================================================================

    async def recover_stale(
        self,
        *,
        timeout_seconds: int,
    ) -> int:
        """
        Recover jobs whose workers stopped sending heartbeats.

        PostgreSQL determines the resulting state.

        If attempts remain:

            running
                ↓
            pending
                ↓
            retry backoff

        If attempts are exhausted:

            running
                ↓
            failed

        Retry policy remains entirely database-owned.
        """

        if not isinstance(
            timeout_seconds,
            int,
        ):
            raise TypeError(
                "timeout_seconds must be an integer.",
            )

        if timeout_seconds < 1:
            raise ValueError(
                "timeout_seconds must be greater than "
                "or equal to 1.",
            )

        try:
            response = self._client.rpc(
                "recover_stale_background_jobs",
                {
                    "p_timeout_seconds": timeout_seconds,
                },
            ).execute()

        except Exception:
            logger.exception(
                "[BackgroundJobRPC] "
                "Failed to recover stale jobs: "
                "timeout=%s",
                timeout_seconds,
            )
            raise

        recovered = response.data or []

        if not isinstance(
            recovered,
            list,
        ):
            raise TypeError(
                "recover_stale_background_jobs returned "
                "an invalid response.",
            )

        recovered_count = len(
            recovered,
        )

        if recovered_count:
            logger.warning(
                "[BackgroundJobRPC] "
                "Recovered stale jobs: "
                "count=%s "
                "timeout=%ss",
                recovered_count,
                timeout_seconds,
            )

        return recovered_count

    # ==================================================================
    # VALIDATION HELPERS
    # ==================================================================

    @staticmethod
    def _validate_job_id(
        job_id: str,
    ) -> str:
        """
        Validate and normalize a background-job ID.
        """

        if not isinstance(
            job_id,
            str,
        ):
            raise TypeError(
                "job_id must be a string.",
            )

        job_id = job_id.strip()

        if not job_id:
            raise ValueError(
                "job_id is required.",
            )

        return job_id

    @staticmethod
    def _validate_job_type(
        job_type: str,
    ) -> str:
        """
        Validate and normalize a background-job type.
        """

        if not isinstance(
            job_type,
            str,
        ):
            raise TypeError(
                "job_type must be a string.",
            )

        job_type = job_type.strip()

        if not job_type:
            raise ValueError(
                "job_type is required.",
            )

        return job_type

    @staticmethod
    def _validate_worker_name(
        worker_name: str,
    ) -> str:
        """
        Validate and normalize a worker name.
        """

        if not isinstance(
            worker_name,
            str,
        ):
            raise TypeError(
                "worker_name must be a string.",
            )

        worker_name = worker_name.strip()

        if not worker_name:
            raise ValueError(
                "worker_name is required.",
            )

        return worker_name

    @staticmethod
    def _normalize_run_at(
        run_at: str | None,
    ) -> str | None:
        """
        Validate and normalize an execution timestamp.

        The background-job system operates using timezone-aware
        UTC timestamps.

        Naive timestamps are rejected.
        """

        if run_at is None:
            return None

        if not isinstance(
            run_at,
            str,
        ):
            raise TypeError(
                "run_at must be an ISO-8601 string.",
            )

        value = run_at.strip()

        if not value:
            raise ValueError(
                "run_at cannot be empty.",
            )

        try:
            parsed = datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                ),
            )

        except ValueError as exc:
            raise ValueError(
                "run_at must be a valid ISO-8601 timestamp.",
            ) from exc

        if parsed.tzinfo is None:
            raise ValueError(
                "run_at must include timezone information.",
            )

        return parsed.astimezone(
            timezone.utc,
        ).isoformat()

    @staticmethod
    def _utc_now() -> str:
        """
        Return the current UTC timestamp as ISO-8601.
        """

        return datetime.now(
            timezone.utc,
        ).isoformat()
