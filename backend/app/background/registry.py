from __future__ import annotations

import logging
from typing import Iterable

from .worker import BackgroundWorker


logger = logging.getLogger(__name__)


class WorkerRegistry:
    """
    Registry of background workers.

    Each job type maps to exactly one BackgroundWorker.

    Responsibilities:
        - Register workers.
        - Resolve workers by job type.
        - Remove workers.
        - Expose registered workers.

    The registry does NOT:
        - Execute jobs.
        - Claim jobs.
        - Handle retries.
        - Handle heartbeats.
        - Schedule jobs.
        - Communicate with the database.

    Those responsibilities belong to the runner, RPC layer,
    and APScheduler infrastructure.
    """

    def __init__(
        self,
        workers: Iterable[BackgroundWorker] | None = None,
    ) -> None:
        self._workers: dict[str, BackgroundWorker] = {}

        if workers is not None:
            self.register_many(workers)

    def register(
        self,
        worker: BackgroundWorker,
    ) -> None:
        """
        Register a worker for its job type.

        Each job type can only have one registered worker.

        Raises:
            ValueError:
                If the worker is invalid or the job type is
                already registered.

            TypeError:
                If worker is not a BackgroundWorker.
        """

        if worker is None:
            raise ValueError(
                "Background worker cannot be None.",
            )

        if not isinstance(
            worker,
            BackgroundWorker,
        ):
            raise TypeError(
                "worker must be an instance of BackgroundWorker.",
            )

        job_type = worker.job_type

        if not isinstance(
            job_type,
            str,
        ):
            raise TypeError(
                "Worker job_type must be a string.",
            )

        if not job_type.strip():
            raise ValueError(
                "Worker job_type cannot be empty.",
            )

        normalized_job_type = job_type.strip()

        if normalized_job_type != job_type:
            raise ValueError(
                "Worker job_type cannot contain leading or "
                "trailing whitespace.",
            )

        if normalized_job_type in self._workers:
            existing = self._workers[
                normalized_job_type
            ]

            raise ValueError(
                f"Worker already registered for job type "
                f"'{normalized_job_type}': "
                f"{type(existing).__name__}",
            )

        self._workers[
            normalized_job_type
        ] = worker

        logger.info(
            "[WorkerRegistry] Worker registered: "
            "job_type=%s worker=%s worker_name=%s",
            normalized_job_type,
            type(worker).__name__,
            worker.worker_name,
        )

    def register_many(
        self,
        workers: Iterable[BackgroundWorker],
    ) -> None:
        """
        Register multiple workers.

        Registration is performed sequentially through register(),
        so duplicate job types are rejected.
        """

        if workers is None:
            raise ValueError(
                "workers cannot be None.",
            )

        for worker in workers:
            self.register(
                worker,
            )

    def unregister(
        self,
        job_type: str,
    ) -> BackgroundWorker | None:
        """
        Remove and return a worker if registered.

        Returns:
            The removed worker, or None if no worker exists.
        """

        job_type = self._normalize_job_type(
            job_type,
        )

        worker = self._workers.pop(
            job_type,
            None,
        )

        if worker is not None:
            logger.info(
                "[WorkerRegistry] Worker unregistered: "
                "job_type=%s worker=%s worker_name=%s",
                job_type,
                type(worker).__name__,
                worker.worker_name,
            )

        return worker

    def get(
        self,
        job_type: str,
    ) -> BackgroundWorker:
        """
        Resolve the worker responsible for a job type.

        Raises:
            LookupError:
                If no worker is registered.
        """

        job_type = self._normalize_job_type(
            job_type,
        )

        worker = self._workers.get(
            job_type,
        )

        if worker is None:
            raise LookupError(
                f"No background worker registered "
                f"for job type '{job_type}'.",
            )

        return worker

    def has(
        self,
        job_type: str,
    ) -> bool:
        """
        Return whether a worker is registered.
        """

        job_type = self._normalize_job_type(
            job_type,
        )

        return job_type in self._workers

    def all(
        self,
    ) -> tuple[BackgroundWorker, ...]:
        """
        Return all registered workers.

        Workers preserve registration order.
        """

        return tuple(
            self._workers.values(),
        )

    def job_types(
        self,
    ) -> tuple[str, ...]:
        """
        Return all registered job types.

        Job types preserve registration order.
        """

        return tuple(
            self._workers.keys(),
        )

    def clear(
        self,
    ) -> None:
        """
        Remove all registered workers.

        Useful during testing, shutdown, or registry
        reinitialization.
        """

        count = len(
            self._workers,
        )

        self._workers.clear()

        if count:
            logger.info(
                "[WorkerRegistry] Registry cleared: "
                "workers=%s",
                count,
            )

    def __contains__(
        self,
        job_type: str,
    ) -> bool:
        return self.has(
            job_type,
        )

    def __len__(
        self,
    ) -> int:
        return len(
            self._workers,
        )

    def __repr__(
        self,
    ) -> str:
        return (
            f"{type(self).__name__}("
            f"job_types={self.job_types()!r}"
            f")"
        )

    @staticmethod
    def _normalize_job_type(
        job_type: str,
    ) -> str:
        """
        Validate and normalize a job type used for lookup.
        """

        if not isinstance(
            job_type,
            str,
        ):
            raise TypeError(
                "job_type must be a string.",
            )

        normalized = job_type.strip()

        if not normalized:
            raise ValueError(
                "job_type cannot be empty.",
            )

        return normalized
