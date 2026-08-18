from __future__ import annotations

import logging

from .interfaces import BackgroundJobRPC
from .runner import BackgroundRunner


logger = logging.getLogger(__name__)


class BackgroundDispatcher:
    """
    Coordinates the generic background-job infrastructure.

    The dispatcher contains no job-specific business logic.

    Responsibilities:
        - Dispatch pending jobs through BackgroundRunner.
        - Recover stale jobs through BackgroundJobRPC.
        - Provide independent operations for APScheduler.

    APScheduler should schedule:

        dispatch_once()
            frequently

        recover_once()
            less frequently

    Example:

        scheduler.add_job(
            dispatcher.dispatch_once,
            "interval",
            seconds=5,
        )

        scheduler.add_job(
            dispatcher.recover_once,
            "interval",
            seconds=60,
        )

    The dispatcher does NOT:
        - Calculate retry delays.
        - Sleep for retries.
        - Claim jobs directly.
        - Execute workers directly.
        - Persist job state directly.
        - Contain job-specific logic.

    PostgreSQL owns durable job state and retry scheduling.
    """

    def __init__(
        self,
        *,
        rpc: BackgroundJobRPC,
        runner: BackgroundRunner,
        batch_size: int = 10,
        recovery_timeout: int = 300,
    ) -> None:

        if batch_size <= 0:
            raise ValueError(
                "batch_size must be greater than zero.",
            )

        if recovery_timeout <= 0:
            raise ValueError(
                "recovery_timeout must be greater than zero.",
            )

        self._rpc = rpc
        self._runner = runner
        self._batch_size = batch_size
        self._recovery_timeout = recovery_timeout

    @property
    def rpc(self) -> BackgroundJobRPC:
        """Return the background-job RPC implementation."""

        return self._rpc

    @property
    def runner(self) -> BackgroundRunner:
        """Return the background runner."""

        return self._runner

    @property
    def batch_size(self) -> int:
        """Return the configured dispatch batch size."""

        return self._batch_size

    @property
    def recovery_timeout(self) -> int:
        """Return the stale-job timeout in seconds."""

        return self._recovery_timeout

    async def dispatch_once(self) -> int:
        """
        Claim and execute one batch of pending jobs.

        PostgreSQL is responsible for:

            - Selecting eligible jobs.
            - Concurrency control.
            - FOR UPDATE SKIP LOCKED.
            - Incrementing attempts.
            - Marking jobs as running.
            - Respecting scheduled_at.

        BackgroundRunner is responsible for:

            - Resolving the appropriate worker.
            - Executing the worker.
            - Maintaining heartbeats.
            - Completing jobs.
            - Requesting failure/retry.

        Returns:
            Number of jobs claimed.
        """

        try:

            count = await self._runner.run_once(
                limit=self._batch_size,
            )

            if count > 0:

                logger.info(
                    "[BackgroundDispatcher] "
                    "Dispatch completed: "
                    "worker=%s claimed=%s",
                    self._runner.worker_name,
                    count,
                )

            return count

        except Exception:

            logger.exception(
                "[BackgroundDispatcher] "
                "Dispatch cycle failed: worker=%s",
                self._runner.worker_name,
            )

            return 0

    async def recover_once(self) -> int:
        """
        Recover stale running jobs.

        PostgreSQL determines the resulting state.

        If attempts remain:

            running
                ↓
            pending
                ↓
            scheduled_at + retry backoff

        If attempts are exhausted:

            running
                ↓
            failed

        Retry backoff is entirely database-owned.

        The dispatcher never:

            - Sleeps.
            - Calculates retry delays.
            - Changes attempts.
            - Decides whether a retry is allowed.
        """

        try:

            recovered = await self._rpc.recover_stale(
                timeout_seconds=self._recovery_timeout,
            )

            if recovered > 0:

                logger.warning(
                    "[BackgroundDispatcher] "
                    "Recovered stale jobs: count=%s",
                    recovered,
                )

            return recovered

        except Exception:

            logger.exception(
                "[BackgroundDispatcher] "
                "Stale-job recovery failed",
            )

            return 0
