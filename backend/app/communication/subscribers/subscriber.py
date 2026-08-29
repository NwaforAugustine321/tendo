from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.communication.events import ApplicationEvent
from app.communication.interfaces import EventBus

logger = logging.getLogger(__name__)


EventHandler = Callable[
    [ApplicationEvent],
    Awaitable[None],
]

EventFilter = Callable[
    [ApplicationEvent],
    bool,
]


class ApplicationEventSubscriber:
    """
    Subscriber for the application EventBus.

    """

    def __init__(
        self,
        *,
        event_bus: EventBus,
        handler: EventHandler,
        event_filter: EventFilter | None = None,
        name: str = "application-event-subscriber",
    ) -> None:
        self._event_bus = event_bus
        self._handler = handler
        self._event_filter = event_filter
        self._name = name

        self._task: asyncio.Task[None] | None = None

    def start(self) -> asyncio.Task[None]:
        """Start consuming application events."""

        if (
            self._task is not None
            and not self._task.done()
        ):
            return self._task

        self._task = asyncio.create_task(
            self._run(),
            name=self._name,
        )

        logger.info(
            "Application event subscriber started: name=%s",
            self._name,
        )

        return self._task

    async def _run(self) -> None:
        """Consume events from the EventBus."""

        try:
            async for event in self._event_bus.subscribe():

                if not self._matches(
                    event,
                ):
                    continue

                await self._handle(
                    event,
                )

        except asyncio.CancelledError:
            logger.debug(
                "Application event subscriber stopped: name=%s",
                self._name,
            )
            raise

        except Exception:
            logger.exception(
                "Application event subscriber stopped unexpectedly: "
                "name=%s",
                self._name,
            )

    def _matches(
        self,
        event: ApplicationEvent,
    ) -> bool:
        """
        Determine whether the subscriber should process an event.

        If no filter is configured, every event is accepted.
        """

        if self._event_filter is None:
            return True

        try:
            return self._event_filter(
                event,
            )

        except Exception:
            logger.exception(
                "Application event filter failed: "
                "name=%s event=%s id=%s",
                self._name,
                event.event,
                event.id,
            )

            return False

    async def _handle(
        self,
        event: ApplicationEvent,
    ) -> None:
        """Pass an event to the configured handler."""

        try:
            await self._handler(
                event,
            )

        except Exception:
            logger.exception(
                "Failed to handle application event: "
                "name=%s event=%s id=%s correlation_id=%s",
                self._name,
                event.event,
                event.id,
                event.correlation_id,
            )

    async def close(self) -> None:
        """Stop consuming application events."""

        task = self._task

        if task is None:
            return

        self._task = None

        if not task.done():
            task.cancel()

        try:
            await task

        except asyncio.CancelledError:
            pass

        logger.info(
            "Application event subscriber closed: name=%s",
            self._name,
        )
