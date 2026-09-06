
from __future__ import annotations

import logging
from contextlib import suppress
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .config import BackgroundJobConfig
from .dispatcher import BackgroundDispatcher


logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """
    APScheduler integration for background-job recovery.

    The scheduler owns timing only.

    It does NOT:
        - claim jobs
        - execute workers
        - implement retries
        - calculate retry backoff
        - execute background jobs directly
        - communicate with PostgreSQL directly

    It triggers one operation:

        Recovery
            -> BackgroundDispatcher.recover_once()

    BackgroundRunner instances running inside the external
    background worker processes are responsible for:

        - claiming jobs
        - resolving workers
        - executing workers
        - maintaining heartbeats
        - completing jobs
        - requesting failure/retry

    PostgreSQL remains responsible for:

        - durable job state
        - atomic claiming
        - attempts
        - retry eligibility
        - retry backoff
        - scheduled_at
        - stale-job recovery
        - permanent failure
    """

    RECOVERY_JOB_ID = "background-job-recovery"

    def __init__(
        self,
        *,
        dispatcher: BackgroundDispatcher,
        config: BackgroundJobConfig,
    ) -> None:
        if dispatcher is None:
            raise ValueError(
                "dispatcher cannot be None.",
            )

        if config is None:
            raise ValueError(
                "config cannot be None.",
            )

        config.validate()

        self._dispatcher = dispatcher
        self._config = config

        self._scheduler = AsyncIOScheduler(
            timezone=self._config.timezone,
        )

        self._started = False

    @property
    def scheduler(self) -> AsyncIOScheduler:
        """
        Return the underlying APScheduler instance.
        """

        return self._scheduler

    @property
    def dispatcher(self) -> BackgroundDispatcher:
        """
        Return the background dispatcher.
        """

        return self._dispatcher

    @property
    def config(self) -> BackgroundJobConfig:
        """
        Return the scheduler configuration.
        """

        return self._config

    @property
    def started(self) -> bool:
        """
        Return whether APScheduler is currently running.
        """

        return self._started

    def start(self) -> None:
        """
        Register the recovery job and start APScheduler.

        APScheduler is responsible only for triggering stale-job
        recovery. Background job execution is handled by the
        external background worker processes.
        """

        if self._started:
            logger.warning(
                "[BackgroundScheduler] "
                "Scheduler already started.",
            )
            return

        self._config.validate()

        self._register_jobs()

        try:
            self._scheduler.start()

        except Exception:
            logger.exception(
                "[BackgroundScheduler] "
                "Failed to start scheduler.",
            )

            self._started = False

            raise

        self._started = True

        logger.info(
            "[BackgroundScheduler] Scheduler started: "
            "timezone=%s "
            "recovery_interval=%ss "
            "recovery_timeout=%ss",
            self._config.timezone,
            self._config.recovery_interval_seconds,
            self._config.recovery_timeout_seconds,
        )

    async def shutdown(
        self,
        *,
        wait: bool = True,
    ) -> None:
        """
        Shut down APScheduler.

        APScheduler's AsyncIOScheduler.shutdown() is a
        synchronous method, so it is intentionally not awaited.

        Args:
            wait:
                Whether currently executing scheduler jobs should
                be allowed to finish.
        """

        if not self._started:
            return

        logger.info(
            "[BackgroundScheduler] "
            "Shutting down scheduler.",
        )

        try:
            self._scheduler.shutdown(
                wait=wait,
            )

        except Exception:
            logger.exception(
                "[BackgroundScheduler] "
                "Scheduler shutdown failed.",
            )

            raise

        finally:
            self._started = False

        logger.info(
            "[BackgroundScheduler] "
            "Scheduler stopped.",
        )

    def _register_jobs(self) -> None:
        """
        Register the stale-job recovery job.
        """

        self._scheduler.add_job(
            self._recover,
            trigger=IntervalTrigger(
                seconds=self._config.recovery_interval_seconds,
                timezone=self._config.timezone,
            ),
            id=self.RECOVERY_JOB_ID,
            name="Background Job Recovery",
            replace_existing=True,
            max_instances=self._config.max_recovery_instances,
            coalesce=True,
            misfire_grace_time=max(
                1,
                int(
                    self._config.recovery_interval_seconds,
                ),
            ),
        )

        logger.info(
            "[BackgroundScheduler] "
            "Scheduled recovery job: "
            "interval=%ss",
            self._config.recovery_interval_seconds,
        )

    async def _recover(self) -> None:
        """
        APScheduler callback for stale-job recovery.

        PostgreSQL determines which jobs are stale and whether
        each recovered job returns to pending or becomes failed.
        """

        try:
            recovered = await self._dispatcher.recover_once()

            if recovered > 0:
                logger.info(
                    "[BackgroundScheduler] "
                    "Recovery cycle completed: "
                    "recovered=%s",
                    recovered,
                )

        except Exception:
            logger.exception(
                "[BackgroundScheduler] "
                "Recovery job failed.",
            )

    def remove_jobs(self) -> None:
        """
        Remove the background recovery job.

        This does not shut down APScheduler itself.

        Useful for:
            - testing
            - scheduler reconfiguration
            - controlled job replacement
        """

        with suppress(Exception):
            self._scheduler.remove_job(
                self.RECOVERY_JOB_ID,
            )

        logger.info(
            "[BackgroundScheduler] "
            "Background scheduler jobs removed.",
        )

    def get_jobs(self) -> list[Any]:
        """
        Return currently registered APScheduler jobs.
        """

        return self._scheduler.get_jobs()

    def get_job(
        self,
        job_id: str,
    ) -> Any | None:
        """
        Return a specific APScheduler job.

        Returns:
            The APScheduler job or None if it is not registered.
        """

        if not isinstance(
            job_id,
            str,
        ):
            return None

        job_id = job_id.strip()

        if not job_id:
            return None

        return self._scheduler.get_job(
            job_id,
        )

    def is_recovery_scheduled(self) -> bool:
        """
        Return whether the recovery job is registered.
        """

        return (
            self.get_job(
                self.RECOVERY_JOB_ID,
            )
            is not None
        )
