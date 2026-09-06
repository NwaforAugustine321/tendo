
from __future__ import annotations

import logging

from .interfaces import BackgroundJobRPC


logger = logging.getLogger(__name__)


class BackgroundDispatcher:
    """
    Coordinates background-job recovery.

    Responsibilities:
        - Recover stale jobs through BackgroundJobRPC.
        - Provide recovery operations for the scheduler.

    The dispatcher does NOT:
        - Execute jobs.
        - Claim jobs for execution.
        - Resolve workers.
        - Maintain worker heartbeats.
        - Calculate retry delays.
        - Sleep for retries.
        - Persist job state directly.
        - Contain job-specific logic.

    Job execution is owned by BackgroundRunner instances running
    inside the external background worker processes.

    PostgreSQL owns durable job state and retry scheduling.
    """

    def __init__(
        self,
        *,
        rpc: BackgroundJobRPC,
        recovery_timeout: int = 300,
    ) -> None:

        if recovery_timeout <= 0:
            raise ValueError(
                "recovery_timeout must be greater than zero.",
            )

        self._rpc = rpc
        self._recovery_timeout = recovery_timeout

    @property
    def rpc(self) -> BackgroundJobRPC:
        """Return the background-job RPC implementation."""

        return self._rpc

    @property
    def recovery_timeout(self) -> int:
        """Return the stale-job timeout in seconds."""

        return self._recovery_timeout

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

            - Executes jobs.
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
