from __future__ import annotations

import asyncio
import logging

from app.communication.events import ApplicationEvent
from app.communication.interfaces import EventBus

from .lifecycle import VoiceLifecycleService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Voice lifecycle events
# ---------------------------------------------------------------------------

VOICE_LIFECYCLE_EVENTS = frozenset(
    {
        "voice.session.requested",
        "voice.session.stop_requested",
    }
)


# ---------------------------------------------------------------------------
# Subscriber
# ---------------------------------------------------------------------------


class VoiceLifecycleSubscriber:
    """
    Subscribes the FastAPI process to voice lifecycle events.

    This subscriber receives only voice lifecycle events and delegates
    their execution to VoiceLifecycleService.

    Lifecycle responsibilities include:

        voice.session.requested
            -> dispatch the LiveKit voice agent

        voice.session.stop_requested
            -> stop the LiveKit voice agent
    """

    def __init__(
        self,
        *,
        event_bus: EventBus,
        service: VoiceLifecycleService,
    ) -> None:
        self._event_bus = event_bus
        self._service = service

        self._task: asyncio.Task[None] | None = None

    # -----------------------------------------------------------------------
    # Start
    # -----------------------------------------------------------------------

    def start(self) -> asyncio.Task[None]:
        """
        Start the lifecycle subscriber.

        Calling start() multiple times while the subscriber is already
        running does not create duplicate subscribers.
        """

        if (
            self._task is not None
            and not self._task.done()
        ):
            return self._task

        self._task = asyncio.create_task(
            self._run(),
            name="voice-lifecycle-subscriber",
        )

        logger.info(
            "Voice lifecycle subscriber started.",
        )

        return self._task

    # -----------------------------------------------------------------------
    # Event loop
    # -----------------------------------------------------------------------

    async def _run(self) -> None:
        """
        Consume application events from the EventBus.

        Only voice lifecycle events are forwarded to the lifecycle
        service. All other application events are ignored.
        """

        try:
            async for event in self._event_bus.subscribe():

                if event.event not in VOICE_LIFECYCLE_EVENTS:
                    continue

                await self._handle_event(
                    event,
                )

        except asyncio.CancelledError:
            logger.info(
                "Voice lifecycle subscriber stopped.",
            )
            raise

        except Exception:
            logger.exception(
                "Voice lifecycle subscriber stopped unexpectedly.",
            )

    # -----------------------------------------------------------------------
    # Event handling
    # -----------------------------------------------------------------------

    async def _handle_event(
        self,
        event: ApplicationEvent,
    ) -> None:
        """
        Delegate a lifecycle event to VoiceLifecycleService.
        """

        try:
            logger.info(
                "Processing voice lifecycle event: "
                "event=%s correlation_id=%s",
                event.event,
                event.correlation_id,
            )

            await self._service.handle(
                event,
            )

        except Exception:
            logger.exception(
                "Failed to handle voice lifecycle event: "
                "event=%s correlation_id=%s",
                event.event,
                event.correlation_id,
            )

    # -----------------------------------------------------------------------
    # Close
    # -----------------------------------------------------------------------

    async def close(self) -> None:
        """
        Stop the lifecycle subscriber.
        """

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
            "Voice lifecycle subscriber closed.",
        )
