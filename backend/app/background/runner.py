
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

    A runner operates inside one background worker process.

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
        - Contain job-specific logic.

    Those responsibilities belong to the database,
    BackgroundScheduler/BackgroundDispatcher, and registered
    BackgroundWorker implementations.

    Multiple BackgroundRunner instances may operate concurrently
    across separate OS processes. PostgreSQL is responsible for
    atomic job claiming and ownership.
    """

    def __init__(
        self,
        *,
        rpc: BackgroundJobRPC,
        registry: WorkerRegistry,
        worker_name: str,
        heartbeat_interval: float = 30.0,
        max_concurrency: int = 10,
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

        if max_concurrency <= 0:
            raise ValueError(
                "max_concurrency must be greater than zero.",
            )

        self._rpc = rpc
        self._registry = registry
        self._worker_name = worker_name.strip()
        self._heartbeat_interval = heartbeat_interval
        self._max_concurrency = max_concurrency

        # Jobs currently executing in this runner process.
        #
        # run_once() does not await these tasks, so the worker
        # process can continue claiming work while existing jobs
        # remain in flight.
        self._in_flight: set[asyncio.Task[None]] = set()

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

    @property
    def max_concurrency(self) -> int:
        """Return the concurrent job execution budget."""

        return self._max_concurrency

    @property
    def in_flight(self) -> int:
        """Return the number of jobs currently executing."""

        return len(self._in_flight)

    @property
    def available_capacity(self) -> int:
        """Return how many more jobs may be started right now."""

        return max(
            0,
            self._max_concurrency - len(self._in_flight),
        )

    # ------------------------------------------------------------------
    # Job execution dispatch
    # ------------------------------------------------------------------

    async def run_once(
        self,
        *,
        limit: int = 10,
    ) -> int:
        """
        Claim one batch of background jobs and start executing them.

        This method does not wait for the claimed jobs to finish.
        Execution runs in detached tasks so the worker process can
        continue accepting additional work while existing jobs run.

        Only as many jobs as there is free capacity are claimed.

        PostgreSQL atomically claims the jobs, so multiple worker
        processes can safely execute this method concurrently.

        Args:
            limit:
                Maximum number of jobs to claim, further capped by
                the remaining concurrency budget.

        Returns:
            Number of jobs successfully claimed and started.

        Raises:
            Exception:
                Exceptions raised while claiming jobs are allowed
                to propagate to the worker process.
        """

        if limit <= 0:
            return 0

        capacity = self.available_capacity

        if capacity <= 0:
            logger.debug(
                "[BackgroundRunner] At capacity, nothing claimed: "
                "worker=%s in_flight=%s max_concurrency=%s",
                self._worker_name,
                len(self._in_flight),
                self._max_concurrency,
            )

            return 0

        jobs = await self._rpc.claim(
            worker_name=self._worker_name,
            limit=min(
                limit,
                capacity,
            ),
        )

        if not jobs:
            return 0

        for job in jobs:
            task = asyncio.create_task(
                self._execute(
                    job,
                ),
                name=(
                    "background-job:"
                    f"{job.get('id') if isinstance(job, dict) else '?'}"
                ),
            )

            self._in_flight.add(
                task,
            )

            task.add_done_callback(
                self._on_execution_done,
            )

        logger.info(
            "[BackgroundRunner] Jobs claimed: "
            "worker=%s count=%s in_flight=%s max_concurrency=%s",
            self._worker_name,
            len(jobs),
            len(self._in_flight),
            self._max_concurrency,
        )

        return len(jobs)

    def _on_execution_done(
        self,
        task: asyncio.Task[None],
    ) -> None:
        """
        Release execution capacity and surface unexpected runner errors.

        Job execution failures are handled by _execute() and persisted
        through the durable RPC layer. Exceptions reaching this callback
        are therefore unexpected runner-level failures.
        """

        self._in_flight.discard(
            task,
        )

        if task.cancelled():
            return

        exc = task.exception()

        if exc is not None:
            logger.error(
                "[BackgroundRunner] "
                "Unexpected execution error: task=%s",
                task.get_name(),
                exc_info=exc,
            )

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def drain(
        self,
        *,
        timeout: float | None = None,
    ) -> int:
        """
        Wait for in-flight jobs to finish.

        Worker processes call this during graceful shutdown so
        currently executing jobs have an opportunity to complete
        before the process exits.

        Args:
            timeout:
                Seconds to wait before giving up. None waits
                indefinitely.

        Returns:
            Number of jobs still in flight after draining.

        Note:
            Jobs still running when the process exits are eventually
            handled by stale-job recovery through the scheduler.
        """

        if not self._in_flight:
            return 0

        pending = set(
            self._in_flight,
        )

        logger.info(
            "[BackgroundRunner] Draining in-flight jobs: "
            "worker=%s count=%s timeout=%s",
            self._worker_name,
            len(pending),
            timeout,
        )

        _, still_pending = await asyncio.wait(
            pending,
            timeout=timeout,
        )

        if still_pending:
            logger.warning(
                "[BackgroundRunner] "
                "Drain timed out with jobs still running: "
                "worker=%s count=%s",
                self._worker_name,
                len(still_pending),
            )

        return len(still_pending)

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
            #
            # The worker name is passed so PostgreSQL can verify that
            # the worker completing the job is the worker that owns it.
            # ----------------------------------------------------------

            await self._rpc.complete(
                job_id=job_id,
                worker_name=self._worker_name,
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
                worker_name=self._worker_name,
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
