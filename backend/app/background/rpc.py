
from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from app.db.client import get_client

from .interfaces import BackgroundJobRPC, IntervalUnit


logger = logging.getLogger(__name__)


TABLE_NAME = "background_jobs"

DEFAULT_MAX_ATTEMPTS = 8

MAX_ERROR_LENGTH = 10000


class DatabaseBackgroundJobRPC(
    BackgroundJobRPC,
):
    """
    PostgreSQL-backed implementation of BackgroundJobRPC.

    PostgreSQL owns:

        - durable job persistence
        - atomic job claiming
        - attempt counting
        - retry decisions
        - retry backoff
        - scheduled execution
        - recurring execution
        - stale-job recovery
        - heartbeat ownership
        - completion ownership
        - failure ownership

    The RPC knows the worker name that currently owns the job.
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
        id: str,
        payload: dict[str, Any] | None = None,
        run_at: str | None = None,
        interval_value: int | None = None,
        interval_unit: IntervalUnit | None = None,
        priority: int = 0,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> str:
        """
        Create a durable background job.

        id:
            ID that owns/created the job.

        run_at:
            First execution time.

        interval_value:
            Number of units between executions.

        interval_unit:
            Unit of recurrence.

        Examples:

            Every 30 seconds:
                interval_value=30
                interval_unit=IntervalUnit.SECONDS

            Every 40 minutes:
                interval_value=40
                interval_unit=IntervalUnit.MINUTES

            Every hour:
                interval_value=1
                interval_unit=IntervalUnit.HOURS

            Every day:
                interval_value=1
                interval_unit=IntervalUnit.DAYS

            Every month:
                interval_value=1
                interval_unit=IntervalUnit.MONTHS

            Every year:
                interval_value=1
                interval_unit=IntervalUnit.YEARS

        The interval is independent of payload.
        """

        job_type = self._validate_job_type(
            job_type,
        )

        id = self._validate_id(
            id,
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

        interval_value, interval_unit = (
            self._validate_interval(
                interval_value=interval_value,
                interval_unit=interval_unit,
            )
        )

        scheduled_at = self._normalize_run_at(
            run_at,
        )

        job_id = id or str(
            uuid4(),
        )

        now = self._utc_now()

        if scheduled_at is None:
            scheduled_at = now

        data = {
            "id": job_id,
            "job_type": job_type,
            "payload": payload or {},
            "status": "pending",
            "priority": priority,
            "attempts": 0,
            "max_attempts": max_attempts,
            "scheduled_at": scheduled_at,
            "interval_value": interval_value,
            "interval_unit": (
                interval_unit.value
                if interval_unit is not None
                else None
            ),
            "created_at": now,
            "updated_at": now,
        }

        try:
            response = (
                self._client
                .table(TABLE_NAME)
                .upsert(data)
                .execute()
            )

        except Exception:
            logger.exception(
                "[BackgroundJobRPC] "
                "Failed to enqueue job: "
                "job_id=%s "
                "job_type=%s ",
                job_id,
                job_type,
            )

            raise

        if not response.data:
            raise RuntimeError(
                "Failed to enqueue background job: "
                f"job_type={job_type} "
                f"job_id={job_id}",
            )

        logger.info(
            "[BackgroundJobRPC] "
            "Job enqueued: "
            "job_id=%s "
            "job_type=%s "
            "scheduled_at=%s "
            "interval=%s %s",
            job_id,
            job_type,
            scheduled_at,
            interval_value,
            (
                interval_unit.value
                if interval_unit is not None
                else None
            ),
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
        worker_name: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        """
        Complete a running job owned by the specified worker.

        PostgreSQL decides what happens next.

        Non-recurring:

            running -> completed

        Recurring:

            running
                ↓
            pending
                ↓
            next scheduled_at

        The same database row is reused.

        The database verifies that worker_name currently owns
        the running job before completion is accepted.
        """

        job_id = self._validate_job_id(
            job_id,
        )

        worker_name = self._validate_worker_name(
            worker_name,
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
                    "p_worker_name": worker_name,
                    "p_result": result or {},
                },
            ).execute()

        except Exception:
            logger.exception(
                "[BackgroundJobRPC] "
                "Failed to complete job: "
                "job_id=%s "
                "worker=%s",
                job_id,
                worker_name,
            )

            raise

        if not response.data:
            raise RuntimeError(
                "Background job could not be completed: "
                f"{job_id} "
                f"worker={worker_name}.",
            )

        updated_job = response.data[0]

        logger.info(
            "[BackgroundJobRPC] "
            "Job completion processed: "
            "job_id=%s "
            "worker=%s "
            "status=%s "
            "scheduled_at=%s",
            job_id,
            worker_name,
            updated_job.get("status"),
            updated_job.get("scheduled_at"),
        )

    # ==================================================================
    # FAIL
    # ==================================================================

    async def fail(
        self,
        *,
        job_id: str,
        worker_name: str,
        error: str,
        retry: bool = True,
    ) -> None:

        job_id = self._validate_job_id(
            job_id,
        )

        worker_name = self._validate_worker_name(
            worker_name,
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
                    "p_worker_name": worker_name,
                    "p_error": error_message,
                    "p_retry": retry,
                },
            ).execute()

        except Exception:
            logger.exception(
                "[BackgroundJobRPC] "
                "Failed to update job failure: "
                "job_id=%s "
                "worker=%s",
                job_id,
                worker_name,
            )

            raise

        if not response.data:
            raise RuntimeError(
                "Background job could not be marked "
                f"as failed: {job_id} "
                f"worker={worker_name}.",
            )

        updated_job = response.data[0]

        logger.warning(
            "[BackgroundJobRPC] "
            "Job failure recorded: "
            "job_id=%s "
            "worker=%s "
            "status=%s "
            "attempts=%s "
            "scheduled_at=%s",
            job_id,
            worker_name,
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
                f"worker={worker_name}.",
            )

    # ==================================================================
    # RECOVER STALE
    # ==================================================================

    async def recover_stale(
        self,
        *,
        timeout_seconds: int,
    ) -> int:

        if not isinstance(
            timeout_seconds,
            int,
        ):
            raise TypeError(
                "timeout_seconds must be an integer.",
            )

        if timeout_seconds < 1:
            raise ValueError(
                "timeout_seconds must be greater "
                "than or equal to 1.",
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

        return len(recovered)

    # ==================================================================
    # VALIDATION
    # ==================================================================

    @staticmethod
    def _validate_id(
        id: str,
    ) -> str:

        if not isinstance(
            id,
            str,
        ):
            raise TypeError(
                "id must be a string.",
            )

        id = id.strip()

        return id

    @staticmethod
    def _validate_interval(
        *,
        interval_value: int | None,
        interval_unit: IntervalUnit | None,
    ) -> tuple[
        int | None,
        IntervalUnit | None,
    ]:

        if (
            interval_value is None
            and interval_unit is None
        ):
            return None, None

        if interval_value is None:
            raise ValueError(
                "interval_value is required when "
                "interval_unit is provided.",
            )

        if interval_unit is None:
            raise ValueError(
                "interval_unit is required when "
                "interval_value is provided.",
            )

        if not isinstance(
            interval_value,
            int,
        ):
            raise TypeError(
                "interval_value must be an integer.",
            )

        if interval_value <= 0:
            raise ValueError(
                "interval_value must be greater than zero.",
            )

        if not isinstance(
            interval_unit,
            IntervalUnit,
        ):
            try:
                interval_unit = IntervalUnit(
                    interval_unit,
                )

            except ValueError as exc:
                raise ValueError(
                    "interval_unit must be one of: "
                    + ", ".join(
                        unit.value
                        for unit in IntervalUnit
                    ),
                ) from exc

        return interval_value, interval_unit

    @staticmethod
    def _validate_job_id(
        job_id: str,
    ) -> str:

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
        return datetime.now(
            timezone.utc,
        ).isoformat()
