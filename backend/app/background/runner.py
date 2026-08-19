from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Any

from .interfaces import BackgroundJobRPC
from .registry import WorkerRegistry


logger = logging.getLogger(__name__)


class BackgroundRunner:
    """
    Generic executor for durable background jobs.

    Responsibilities:
        - Claim jobs from the durable queue.
        - Resolve the appropriate worker.
        - Execute claimed jobs concurrently.
        - Maintain worker heartbeats.
        - Complete successful jobs.
        - Request failure/retry for failed jobs.

    The runner does NOT:
        - Schedule jobs.
        - Calculate retry backoff.
        - Sleep between retries.
        - Recover stale jobs.
        - Contain job-specific user logic.

    Those responsibilities belong to the database, dispatcher,
    and registered BackgroundWorker implementations.
    """

    def __init__(
        self,
        *,
        rpc: BackgroundJobRPC,
        registry: WorkerRegistry,
        worker_name: str,
        heartbeat_interval: float = 30.0,
    ) -> None:
        if rpc is None:
            raise ValueError(
                "rpc cannot be None.",
            )

        if registry is None:
            raise ValueError(
                "registry cannot be None.",
            )

        if not worker_name or not worker_name.strip():
            raise ValueError(
                "worker_name cannot be empty.",
            )

        if heartbeat_interval <= 0:
            raise ValueError(
                "heartbeat_interval must be greater than zero.",
            )

        self._rpc = rpc
        self._registry = registry
        self._worker_name = worker_name.strip()
        self._heartbeat_interval = heartbeat_interval

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def rpc(self) -> BackgroundJobRPC:
        """Return the durable job RPC implementation."""

        return self._rpc

    @property
    def registry(self) -> WorkerRegistry:
        """Return the worker registry."""

        return self._registry

    @property
    def worker_name(self) -> str:
        """Return the logical worker name."""

        return self._worker_name

    @property
    def heartbeat_interval(self) -> float:
        """Return the heartbeat interval in seconds."""

        return self._heartbeat_interval

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def run_once(
        self,
        *,
        limit: int = 10,
    ) -> int:
        """
        Claim and execute one batch of background jobs.

        PostgreSQL atomically claims the jobs, so multiple
        application instances can safely execute this method
        concurrently.

        Args:
            limit:
                Maximum number of jobs to claim.

        Returns:
            Number of jobs successfully claimed.

        Raises:
            Exception:
                Exceptions raised while claiming jobs are allowed
                to propagate to the dispatcher/scheduler.
        """

        if limit <= 0:
            return 0

        jobs = await self._rpc.claim(
            worker_name=self._worker_name,
            limit=limit,
        )

        if not jobs:
            return 0

        logger.info(
            "[BackgroundRunner] Jobs claimed: "
            "worker=%s count=%s",
            self._worker_name,
            len(jobs),
        )

        tasks = [
            asyncio.create_task(
                self._execute(
                    job,
                ),
            )
            for job in jobs
        ]

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        for job, result in zip(
            jobs,
            results,
        ):
            if isinstance(
                result,
                BaseException,
            ):
                logger.error(
                    "[BackgroundRunner] "
                    "Unexpected execution error: "
                    "job_id=%s",
                    job.get("id")
                    if isinstance(job, dict)
                    else None,
                    exc_info=(
                        type(result),
                        result,
                        result.__traceback__,
                    ),
                )

        return len(jobs)

    # ------------------------------------------------------------------
    # Job execution
    # ------------------------------------------------------------------

    async def _execute(
        self,
        job: dict[str, Any],
    ) -> None:
        """
        Execute one claimed background job.
        """

        if not isinstance(
            job,
            dict,
        ):
            logger.error(
                "[BackgroundRunner] "
                "Claimed job is not a dictionary.",
            )
            return

        raw_job_id = job.get(
            "id",
        )

        raw_job_type = job.get(
            "job_type",
        )

        # --------------------------------------------------------------
        # Job ID validation
        # --------------------------------------------------------------

        if not raw_job_id:
            logger.error(
                "[BackgroundRunner] "
                "Claimed job has no ID.",
            )
            return

        job_id = str(
            raw_job_id,
        )

        # --------------------------------------------------------------
        # Job type validation
        # --------------------------------------------------------------

        if not raw_job_type:
            logger.error(
                "[BackgroundRunner] "
                "Claimed job has no job_type: "
                "job_id=%s",
                job_id,
            )

            await self._fail_job(
                job_id=job_id,
                error="Background job has no job_type.",
                retry=False,
            )

            return

        job_type = str(
            raw_job_type,
        )

        # --------------------------------------------------------------
        # Worker resolution
        # --------------------------------------------------------------

        try:
            worker = self._registry.get(
                job_type,
            )

        except LookupError as exc:
            logger.error(
                "[BackgroundRunner] "
                "No worker registered: "
                "job_id=%s job_type=%s",
                job_id,
                job_type,
            )

            await self._fail_job(
                job_id=job_id,
                error=str(exc),
                retry=False,
            )

            return

        heartbeat_task: asyncio.Task[None] | None = None

        try:
            logger.info(
                "[BackgroundRunner] Starting job: "
                "job_id=%s job_type=%s worker=%s "
                "worker_name=%s",
                job_id,
                job_type,
                type(worker).__name__,
                self._worker_name,
            )

            # ----------------------------------------------------------
            # Start heartbeat loop.
            #
            # The heartbeat task runs independently while the worker
            # performs its actual work.
            # ----------------------------------------------------------

            heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(
                    job_id=job_id,
                ),
                name=(
                    f"background-heartbeat:{job_id}"
                ),
            )

            # ----------------------------------------------------------
            # Execute worker.
            # ----------------------------------------------------------

            result = await worker.run(
                job,
            )

            # ----------------------------------------------------------
            # Persist successful completion.
            # ----------------------------------------------------------

            await self._rpc.complete(
                job_id=job_id,
                result=(
                    result
                    if isinstance(
                        result,
                        dict,
                    )
                    else {}
                ),
            )

            logger.info(
                "[BackgroundRunner] Job completed: "
                "job_id=%s job_type=%s worker=%s",
                job_id,
                job_type,
                self._worker_name,
            )

        except asyncio.CancelledError:
            logger.warning(
                "[BackgroundRunner] Job cancelled: "
                "job_id=%s job_type=%s worker=%s",
                job_id,
                job_type,
                self._worker_name,
            )

            raise

        except Exception as exc:
            logger.exception(
                "[BackgroundRunner] Job execution failed: "
                "job_id=%s job_type=%s worker=%s",
                job_id,
                job_type,
                self._worker_name,
            )

            # The database owns:
            #
            #   - current attempt
            #   - max attempts
            #   - retry eligibility
            #   - retry delay
            #   - scheduled_at
            #   - permanent failure
            #
            # Therefore the runner only reports the failure.

            await self._fail_job(
                job_id=job_id,
                error=str(exc),
                retry=True,
            )

        finally:
            # ----------------------------------------------------------
            # Stop heartbeat after execution finishes.
            # ----------------------------------------------------------

            if heartbeat_task is not None:
                heartbeat_task.cancel()

                with suppress(
                    asyncio.CancelledError,
                ):
                    await heartbeat_task

    # ------------------------------------------------------------------
    # Failure persistence
    # ------------------------------------------------------------------

    async def _fail_job(
        self,
        *,
        job_id: str,
        error: str,
        retry: bool,
    ) -> None:
        """
        Persist a job failure.

        Failure persistence errors are logged separately so they
        do not hide the original job execution failure.
        """

        try:
            await self._rpc.fail(
                job_id=job_id,
                error=(
                    error
                    or "Background job failed."
                ),
                retry=retry,
            )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "[BackgroundRunner] "
                "Failed to persist job failure: "
                "job_id=%s",
                job_id,
            )

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    async def _heartbeat_loop(
        self,
        *,
        job_id: str,
    ) -> None:
        """
        Keep the database heartbeat alive while the job runs.

        The worker name is explicitly passed to the RPC layer so
        the durable store can verify ownership of the running job.

        Heartbeat failures do not immediately terminate the job.
        The durable recovery mechanism remains responsible for
        determining whether a job eventually becomes stale.
        """

        try:
            while True:
                await asyncio.sleep(
                    self._heartbeat_interval,
                )

                try:
                    await self._rpc.heartbeat(
                        job_id=job_id,
                        worker_name=self._worker_name,
                    )

                except asyncio.CancelledError:
                    raise

                except Exception:
                    logger.exception(
                        "[BackgroundRunner] "
                        "Heartbeat failed: "
                        "job_id=%s worker=%s",
                        job_id,
                        self._worker_name,
                    )

        except asyncio.CancelledError:
            raise
