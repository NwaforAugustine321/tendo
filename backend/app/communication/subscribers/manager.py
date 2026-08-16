from __future__ import annotations

import logging

from .subscriber import ApplicationEventSubscriber

logger = logging.getLogger(__name__)


class ApplicationEventManager:
    """
    Owns the application's EventBus subscribers.

    The manager is responsible only for subscriber lifecycle:
    registration, startup, and shutdown.

    Individual subscribers decide which events they consume and
    which handlers process those events.
    """

    def __init__(self) -> None:
        self._subscribers: list[
            ApplicationEventSubscriber
        ] = []

        self._started = False

    def register(
        self,
        subscriber: ApplicationEventSubscriber,
    ) -> None:
        """Register an application event subscriber."""

        if self._started:
            raise RuntimeError(
                "Cannot register an event subscriber "
                "after the manager has started.",
            )

        self._subscribers.append(
            subscriber,
        )

    def start(self) -> None:
        """Start all registered subscribers."""

        if self._started:
            return

        self._started = True

        for subscriber in self._subscribers:
            subscriber.start()

        logger.info(
            "Application event manager started: "
            "subscribers=%s",
            len(self._subscribers),
        )

    async def close(self) -> None:
        """Close all registered subscribers."""

        if not self._subscribers:
            return

        for subscriber in reversed(
            self._subscribers,
        ):
            try:
                await subscriber.close()

            except Exception:
                logger.exception(
                    "Failed to close application event subscriber.",
                )

        self._started = False

        logger.info(
            "Application event manager closed.",
        )
