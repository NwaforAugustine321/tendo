from __future__ import annotations

import os
from dataclasses import dataclass

from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class BackgroundJobConfig:
    """
    Configuration for the durable background-job system.

    Architecture:

        APScheduler
            ↓
        dispatch / recovery triggers

        PostgreSQL
            ↓
        durable job state
        retry scheduling
        stale-job recovery

    The scheduler does not calculate retry backoff.
    """

    # ------------------------------------------------------------------
    # Worker identity
    # ------------------------------------------------------------------

    worker_name: str = "background-worker"

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    # Number of jobs claimed during one dispatch cycle.
    batch_size: int = 10

    # How frequently APScheduler triggers dispatch.
    dispatch_interval_seconds: float = 5.0

    # Maximum number of dispatch executions that may overlap
    # inside one application instance.
    max_dispatch_instances: int = 1

    # Maximum number of jobs executing concurrently inside one
    # application instance.
    #
    # Dispatch claims only as many jobs as there is free capacity,
    # so a claimed job always begins executing (and heartbeating)
    # immediately. None falls back to batch_size.
    max_concurrency: int | None = None

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    # How frequently APScheduler checks for stale jobs.
    recovery_interval_seconds: float = 60.0

    # How long a running job can go without a heartbeat before
    # PostgreSQL considers it stale.
    recovery_timeout_seconds: int = 300

    # Maximum number of recovery executions that may overlap
    # inside one application instance.
    max_recovery_instances: int = 1

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    # How frequently a running worker updates its heartbeat.
    heartbeat_interval_seconds: float = 30.0

    # ------------------------------------------------------------------
    # Scheduler
    # ------------------------------------------------------------------

    # APScheduler timezone.
    timezone: str = "UTC"

    # ------------------------------------------------------------------
    # Environment loading
    # ------------------------------------------------------------------

    @classmethod
    def from_env(
        cls,
    ) -> BackgroundJobConfig:
        """
        Build background-job configuration from environment variables.

        Environment variables:

            BACKGROUND_WORKER_NAME
            BACKGROUND_BATCH_SIZE
            BACKGROUND_DISPATCH_INTERVAL
            BACKGROUND_RECOVERY_INTERVAL
            BACKGROUND_RECOVERY_TIMEOUT
            BACKGROUND_HEARTBEAT_INTERVAL
            BACKGROUND_TIMEZONE
            BACKGROUND_MAX_DISPATCH_INSTANCES
            BACKGROUND_MAX_RECOVERY_INSTANCES
            BACKGROUND_MAX_CONCURRENCY
        """

        raw_max_concurrency = os.getenv(
            "BACKGROUND_MAX_CONCURRENCY",
            "",
        ).strip()

        return cls(
            worker_name=os.getenv(
                "BACKGROUND_WORKER_NAME",
                "background-worker",
            ),

            batch_size=int(
                os.getenv(
                    "BACKGROUND_BATCH_SIZE",
                    "10",
                ),
            ),

            dispatch_interval_seconds=float(
                os.getenv(
                    "BACKGROUND_DISPATCH_INTERVAL",
                    "5",
                ),
            ),

            recovery_interval_seconds=float(
                os.getenv(
                    "BACKGROUND_RECOVERY_INTERVAL",
                    "60",
                ),
            ),

            recovery_timeout_seconds=int(
                os.getenv(
                    "BACKGROUND_RECOVERY_TIMEOUT",
                    "300",
                ),
            ),

            heartbeat_interval_seconds=float(
                os.getenv(
                    "BACKGROUND_HEARTBEAT_INTERVAL",
                    "30",
                ),
            ),

            timezone=os.getenv(
                "BACKGROUND_TIMEZONE",
                "UTC",
            ),

            max_dispatch_instances=int(
                os.getenv(
                    "BACKGROUND_MAX_DISPATCH_INSTANCES",
                    "1",
                ),
            ),

            max_recovery_instances=int(
                os.getenv(
                    "BACKGROUND_MAX_RECOVERY_INSTANCES",
                    "1",
                ),
            ),

            max_concurrency=(
                int(raw_max_concurrency)
                if raw_max_concurrency
                else None
            ),
        )

    # ------------------------------------------------------------------
    # Derived values
    # ------------------------------------------------------------------

    @property
    def effective_max_concurrency(self) -> int:
        """
        Concurrency budget actually applied to job execution.

        Defaults to batch_size so behaviour is unchanged until
        BACKGROUND_MAX_CONCURRENCY is set explicitly.
        """

        if self.max_concurrency is None:
            return self.batch_size

        return self.max_concurrency

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """
        Validate the complete background-job configuration.

        Raises:
            ValueError:
                If any configuration value is invalid.
        """

        # --------------------------------------------------------------
        # Worker
        # --------------------------------------------------------------

        if not isinstance(
            self.worker_name,
            str,
        ):
            raise ValueError(
                "BACKGROUND_WORKER_NAME must be a string.",
            )

        if not self.worker_name.strip():
            raise ValueError(
                "BACKGROUND_WORKER_NAME cannot be empty.",
            )

        # --------------------------------------------------------------
        # Dispatch
        # --------------------------------------------------------------

        if self.batch_size <= 0:
            raise ValueError(
                "BACKGROUND_BATCH_SIZE must be greater than zero.",
            )

        if self.dispatch_interval_seconds <= 0:
            raise ValueError(
                "BACKGROUND_DISPATCH_INTERVAL "
                "must be greater than zero.",
            )

        if self.max_dispatch_instances <= 0:
            raise ValueError(
                "BACKGROUND_MAX_DISPATCH_INSTANCES "
                "must be greater than zero.",
            )

        if (
            self.max_concurrency is not None
            and self.max_concurrency <= 0
        ):
            raise ValueError(
                "BACKGROUND_MAX_CONCURRENCY "
                "must be greater than zero.",
            )

        # --------------------------------------------------------------
        # Recovery
        # --------------------------------------------------------------

        if self.recovery_interval_seconds <= 0:
            raise ValueError(
                "BACKGROUND_RECOVERY_INTERVAL "
                "must be greater than zero.",
            )

        if self.recovery_timeout_seconds <= 0:
            raise ValueError(
                "BACKGROUND_RECOVERY_TIMEOUT "
                "must be greater than zero.",
            )

        if self.max_recovery_instances <= 0:
            raise ValueError(
                "BACKGROUND_MAX_RECOVERY_INSTANCES "
                "must be greater than zero.",
            )

        # --------------------------------------------------------------
        # Heartbeat
        # --------------------------------------------------------------

        if self.heartbeat_interval_seconds <= 0:
            raise ValueError(
                "BACKGROUND_HEARTBEAT_INTERVAL "
                "must be greater than zero.",
            )

        if self.heartbeat_interval_seconds >= (
            self.recovery_timeout_seconds
        ):
            raise ValueError(
                "BACKGROUND_HEARTBEAT_INTERVAL must be "
                "smaller than BACKGROUND_RECOVERY_TIMEOUT.",
            )

        # A worker should normally have multiple opportunities
        # to send a heartbeat before it can be considered stale.
        if self.heartbeat_interval_seconds * 2 >= (
            self.recovery_timeout_seconds
        ):
            raise ValueError(
                "BACKGROUND_HEARTBEAT_INTERVAL must be less than "
                "half of BACKGROUND_RECOVERY_TIMEOUT.",
            )

        # --------------------------------------------------------------
        # Timezone
        # --------------------------------------------------------------

        if not isinstance(
            self.timezone,
            str,
        ):
            raise ValueError(
                "BACKGROUND_TIMEZONE must be a string.",
            )

        if not self.timezone.strip():
            raise ValueError(
                "BACKGROUND_TIMEZONE cannot be empty.",
            )

        try:
            ZoneInfo(
                self.timezone,
            )

        except Exception as exc:

            raise ValueError(
                f"Invalid BACKGROUND_TIMEZONE: "
                f"'{self.timezone}'.",
            ) from exc
