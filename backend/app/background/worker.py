from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any


logger = logging.getLogger(__name__)


class BackgroundWorker(ABC):
    """
    Base class for all background workers.

    A worker represents the execution logic for one background
    job type.

    Responsibilities:
        - Validate the job contract.
        - Provide convenient access to job metadata.
        - Execute job-specific processing.

    The worker does NOT handle:
        - Scheduling.
        - Job discovery.
        - Job claiming.
        - Retry policy.
        - Retry backoff.
        - Heartbeats.
        - Job persistence.

    Those responsibilities belong to the background infrastructure.

    Background jobs are scoped to a user through ``user_id``.
    The worker infrastructure does not interpret the meaning of
    that user or any domain-specific entity associated with it.
    """

    def __init__(
        self,
        *,
        job_type: str,
        worker_name: str,
    ) -> None:
        if not isinstance(
            job_type,
            str,
        ):
            raise TypeError(
                "job_type must be a string.",
            )

        if not isinstance(
            worker_name,
            str,
        ):
            raise TypeError(
                "worker_name must be a string.",
            )

        job_type = job_type.strip()
        worker_name = worker_name.strip()

        if not job_type:
            raise ValueError(
                "job_type cannot be empty.",
            )

        if not worker_name:
            raise ValueError(
                "worker_name cannot be empty.",
            )

        self._job_type = job_type
        self._worker_name = worker_name

    # ============================================================
    # Properties
    # ============================================================

    @property
    def job_type(
        self,
    ) -> str:
        """
        Return the job type handled by this worker.
        """

        return self._job_type

    @property
    def worker_name(
        self,
    ) -> str:
        """
        Return the logical worker name.
        """

        return self._worker_name

    # ============================================================
    # Job metadata helpers
    # ============================================================

    @staticmethod
    def get_job_id(
        job: dict[str, Any],
    ) -> str:
        """
        Return the ID of a background job.
        """

        if not isinstance(
            job,
            dict,
        ):
            raise TypeError(
                "Background job must be a dictionary.",
            )

        job_id = job.get(
            "id",
        )

        if not job_id:
            raise ValueError(
                "Background job is missing 'id'.",
            )

        return str(job_id)

    @staticmethod
    def get_user_id(
        job: dict[str, Any],
    ) -> str | None:
        """
        Return the user ID associated with the job.

        Some background jobs may be system-level jobs and therefore
        do not belong to a specific user.
        """

        if not isinstance(
            job,
            dict,
        ):
            raise TypeError(
                "Background job must be a dictionary.",
            )

        user_id = job.get(
            "user_id",
        )

        if user_id is None:
            return None

        return str(
            user_id,
        )

    @staticmethod
    def get_payload(
        job: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Return the job payload.

        Every background job should use a JSON object as its
        payload.
        """

        if not isinstance(
            job,
            dict,
        ):
            raise TypeError(
                "Background job must be a dictionary.",
            )

        payload = job.get(
            "payload",
        )

        if payload is None:
            return {}

        if not isinstance(
            payload,
            dict,
        ):
            raise TypeError(
                "Background job 'payload' must be a dictionary.",
            )

        return payload

    # ============================================================
    # Public execution boundary
    # ============================================================

    async def run(
        self,
        job: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Execute a background job.

        This is the public execution boundary used by
        BackgroundRunner.

        Exceptions intentionally propagate to the runner so the
        durable job system can record the failure and apply the
        database retry policy.
        """

        self._validate_job(
            job,
        )

        job_id = self.get_job_id(
            job,
        )

        logger.info(
            "[BackgroundWorker] Starting job: "
            "job_id=%s job_type=%s worker=%s",
            job_id,
            self.job_type,
            self.worker_name,
        )

        try:
            result = await self.process(
                job,
            )

        except Exception:
            logger.exception(
                "[BackgroundWorker] Job processing failed: "
                "job_id=%s job_type=%s worker=%s",
                job_id,
                self.job_type,
                self.worker_name,
            )

            raise

        logger.info(
            "[BackgroundWorker] Finished job: "
            "job_id=%s job_type=%s worker=%s",
            job_id,
            self.job_type,
            self.worker_name,
        )

        return result

    # ============================================================
    # Validation
    # ============================================================

    def _validate_job(
        self,
        job: dict[str, Any],
    ) -> None:
        """
        Validate the basic background-job contract.
        """

        if not isinstance(
            job,
            dict,
        ):
            raise TypeError(
                "Background job must be a dictionary.",
            )

        # --------------------------------------------------------
        # ID
        # --------------------------------------------------------

        job_id = job.get(
            "id",
        )

        if not job_id:
            raise ValueError(
                "Background job is missing 'id'.",
            )

        # --------------------------------------------------------
        # Job type
        # --------------------------------------------------------

        job_type = job.get(
            "job_type",
        )

        if not job_type:
            raise ValueError(
                "Background job is missing 'job_type'.",
            )

        if not isinstance(
            job_type,
            str,
        ):
            raise TypeError(
                "Background job 'job_type' must be a string.",
            )

        if job_type != self.job_type:
            raise ValueError(
                f"Job type mismatch: expected "
                f"'{self.job_type}', got '{job_type}'.",
            )

        # --------------------------------------------------------
        # Payload
        # --------------------------------------------------------

        payload = job.get(
            "payload",
        )

        if (
            payload is not None
            and not isinstance(
                payload,
                dict,
            )
        ):
            raise TypeError(
                "Background job 'payload' must be a dictionary.",
            )

        # --------------------------------------------------------
        # Attempts
        # --------------------------------------------------------

        attempts = job.get(
            "attempts",
        )

        if attempts is not None:

            if (
                isinstance(
                    attempts,
                    bool,
                )
                or not isinstance(
                    attempts,
                    int,
                )
            ):
                raise TypeError(
                    "Background job 'attempts' must be an integer.",
                )

            if attempts < 0:
                raise ValueError(
                    "Background job 'attempts' cannot be negative.",
                )

        # --------------------------------------------------------
        # Max attempts
        # --------------------------------------------------------

        max_attempts = job.get(
            "max_attempts",
        )

        if max_attempts is not None:

            if (
                isinstance(
                    max_attempts,
                    bool,
                )
                or not isinstance(
                    max_attempts,
                    int,
                )
            ):
                raise TypeError(
                    "Background job 'max_attempts' "
                    "must be an integer.",
                )

            if max_attempts < 1:
                raise ValueError(
                    "Background job 'max_attempts' "
                    "must be greater than zero.",
                )

        # --------------------------------------------------------
        # Attempts consistency
        # --------------------------------------------------------

        if (
            attempts is not None
            and max_attempts is not None
            and attempts > max_attempts
        ):
            raise ValueError(
                "Background job 'attempts' cannot be greater "
                "than 'max_attempts'.",
            )

    # ============================================================
    # Job-specific processing
    # ============================================================

    @abstractmethod
    async def process(
        self,
        job: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Execute the actual job-specific work.

        Subclasses implement this method.

        Args:
            job:
                Claimed background job containing fields such as:

                    id
                    job_type
                    user_id
                    payload
                    attempts
                    max_attempts
                    priority
                    scheduled_at

        Returns:
            Optional structured JSON-serializable result.

        Raises:
            Exception:
                Processing exceptions propagate to
                BackgroundRunner. The runner persists the failure
                and delegates retry/backoff decisions to PostgreSQL.
        """
        ...
