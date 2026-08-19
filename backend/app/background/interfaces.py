from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from enum import StrEnum


class BackgroundJobRPC(ABC):
    """
    Interface for durable background-job coordination.

    Implementations communicate with the durable job store.

    The RPC layer does NOT:
        - Execute jobs.
        - Resolve workers.
        - Implement business logic.
        - Calculate retry backoff.
        - Sleep between retries.

    Responsibilities:
        - Enqueue jobs.
        - Atomically claim jobs.
        - Complete jobs.
        - Fail/retry jobs.
        - Update heartbeats.
        - Recover stale jobs.

    Retry policy and retry scheduling are owned entirely by the
    durable database layer.
    """

    @abstractmethod
    async def enqueue(
        self,
        *,
        job_type: str,
        id: str | None = None,
        payload: dict[str, Any] | None = None,
        run_at: str | None = None,
        priority: int = 0,
        max_attempts: int = 8,
    ) -> str:
        """
        Create a durable background job.

        Args:
            job_type:
                Logical type of the job.

            id:
                Optional id associated with the job.

            payload:
                Job-specific input data.

            run_at:
                Optional ISO-8601 timestamp at which the job
                becomes eligible for execution.

            priority:
                Higher values are processed before lower values.

            max_attempts:
                Maximum number of execution attempts.

        Returns:
            The newly created job ID.
        """
        ...

    @abstractmethod
    async def claim(
        self,
        *,
        worker_name: str,
        limit: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Atomically claim pending jobs.

        The durable store must guarantee that concurrent
        application instances cannot claim the same job.

        The implementation is responsible for:

            pending
                ↓
            running

        and for assigning the claimed jobs to the
        requesting worker.
        """
        ...

    @abstractmethod
    async def complete(
        self,
        *,
        job_id: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        """
        Mark a running job as successfully completed.

        The durable store must ensure that only an eligible
        running job can transition to completed.
        """
        ...

    @abstractmethod
    async def fail(
        self,
        *,
        job_id: str,
        error: str,
        retry: bool = True,
    ) -> None:
        """
        Fail a running job or schedule it for retry.

        The durable database determines:

            - whether another attempt is available
            - retry delay
            - next scheduled_at
            - permanent failure

        The worker must never sleep for retry backoff.
        """
        ...

    @abstractmethod
    async def heartbeat(
        self,
        *,
        job_id: str,
        worker_name: str,
    ) -> None:
        """
        Update the heartbeat of a running job.

        The durable store must verify the worker name so that
        one worker cannot accidentally update another worker's
        claimed job.
        """
        ...

    @abstractmethod
    async def recover_stale(
        self,
        *,
        timeout_seconds: int,
    ) -> int:
        """
        Recover jobs whose workers stopped sending heartbeats.

        The durable store determines the appropriate transition:

            running -> pending

        when another attempt is available, or:

            running -> failed

        when the job has exhausted its attempts.

        Retry scheduling and backoff remain entirely owned by
        the durable database.
        """
        ...


class IntervalUnit(StrEnum):
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"
