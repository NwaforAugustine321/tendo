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


class ApplicationEventSubscriber:
    """
    Application-event subscriber.

    Receives events from the application EventBus and forwards
    them to the configured handler.
    """

    def __init__(
        self,
        *,
        event_bus: EventBus,
        handler: EventHandler,
    ) -> None:
        self._event_bus = event_bus
        self._handler = handler
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
            name="application-event-subscriber",
        )

        return self._task

    async def _run(self) -> None:
        try:
            async for event in self._event_bus.subscribe():
                await self._handle(
                    event,
                )

        except asyncio.CancelledError:
            logger.debug(
                "Application event subscriber stopped.",
            )
            raise

        except Exception:
            logger.exception(
                "Application event subscriber stopped unexpectedly.",
            )

    async def _handle(
        self,
        event: ApplicationEvent,
    ) -> None:
        try:
            await self._handler(
                event,
            )

        except Exception:
            logger.exception(
                "Failed to handle application event: %s",
                event.event,
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
