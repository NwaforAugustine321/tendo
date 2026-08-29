from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass

from livekit.agents import AgentSession

from app.communication.events import ApplicationEvent
from app.communication.interfaces import EventBus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

VOICE_AGENT_SOURCE = "voice-agent"

VOICE_LIFECYCLE_EVENTS = frozenset(
    {
        "voice.session.requested",
        "voice.session.stop_requested",
    }
)

EventHandler = Callable[
    [ApplicationEvent],
    Awaitable[None],
]

_INBOX_CLOSED = object()


# ---------------------------------------------------------------------------
# Voice session inbox
# ---------------------------------------------------------------------------


class VoiceSessionEventInbox:
    """Asynchronous application-event inbox for one voice session."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[
            ApplicationEvent | object
        ] = asyncio.Queue()

        self._closed = False

    async def put(
        self,
        event: ApplicationEvent,
    ) -> None:
        """Add an application event to the inbox."""

        if self._closed:
            return

        await self._queue.put(
            event,
        )

    async def receive(
        self,
    ) -> ApplicationEvent | None:
        """
        Wait for the next application event.

        Returns None when the inbox is closed.
        """

        item = await self._queue.get()

        if item is _INBOX_CLOSED:
            return None

        return item

    async def events(
        self,
    ) -> AsyncIterator[ApplicationEvent]:
        """Yield application events until the inbox is closed."""

        while True:
            event = await self.receive()

            if event is None:
                return

            yield event

    def close(self) -> None:
        """Close the inbox and wake any waiting consumer."""

        if self._closed:
            return

        self._closed = True

        self._queue.put_nowait(
            _INBOX_CLOSED,
        )


# ---------------------------------------------------------------------------
# Voice session registry
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class VoiceSessionEntry:
    """Runtime state associated with an active voice session."""

    session: AgentSession
    inbox: VoiceSessionEventInbox


class VoiceSessionRegistry:
    """Tracks active voice sessions and their event inboxes."""

    def __init__(self) -> None:
        self._sessions: dict[
            str,
            VoiceSessionEntry,
        ] = {}

        self._lock = asyncio.Lock()

    async def register(
        self,
        session_id: str,
        session: AgentSession,
    ) -> VoiceSessionEventInbox:
        """
        Register a voice session and create its event inbox.

        If a session already exists for the same ID, its previous
        inbox is closed before being replaced.
        """

        inbox = VoiceSessionEventInbox()

        entry = VoiceSessionEntry(
            session=session,
            inbox=inbox,
        )

        async with self._lock:
            previous = self._sessions.get(
                session_id,
            )

            self._sessions[
                session_id
            ] = entry

        if previous is not None:
            previous.inbox.close()

        logger.info(
            "Voice session registered: session_id=%s",
            session_id,
        )

        return inbox

    async def get(
        self,
        session_id: str,
    ) -> VoiceSessionEntry | None:
        """Return a registered voice session."""

        async with self._lock:
            return self._sessions.get(
                session_id,
            )

    async def dispatch(
        self,
        event: ApplicationEvent,
    ) -> bool:
        """
        Dispatch a runtime application event to its target
        voice session.

        Returns True when the event was delivered.
        """

        correlation_id = event.correlation_id

        if not correlation_id:
            return False

        entry = await self.get(
            correlation_id,
        )

        if entry is None:
            return False

        await entry.inbox.put(
            event,
        )

        logger.debug(
            "Voice runtime event delivered: "
            "event=%s correlation_id=%s",
            event.event,
            correlation_id,
        )

        return True

    async def unregister(
        self,
        session_id: str,
    ) -> None:
        """Remove and close a voice session."""

        async with self._lock:
            entry = self._sessions.pop(
                session_id,
                None,
            )

        if entry is None:
            return

        entry.inbox.close()

        logger.info(
            "Voice session unregistered: session_id=%s",
            session_id,
        )

    async def clear(self) -> None:
        """Remove and close all registered sessions."""

        async with self._lock:
            entries = list(
                self._sessions.values(),
            )

            self._sessions.clear()

        for entry in entries:
            entry.inbox.close()

    async def close(self) -> None:
        """Close the registry."""

        await self.clear()


# ---------------------------------------------------------------------------
# Voice agent event router
# ---------------------------------------------------------------------------


class VoiceAgentEventRouter:
    """
    Routes runtime application events to active voice sessions.

    Lifecycle events are deliberately excluded because they belong
    to VoiceLifecycleSubscriber.
    """

    def __init__(
        self,
        *,
        registry: VoiceSessionRegistry,
    ) -> None:
        self._registry = registry

    async def handle(
        self,
        event: ApplicationEvent,
    ) -> None:
        """
        Route one runtime application event to its target
        voice session.
        """

        # ---------------------------------------------------------------
        # Ignore events generated by the voice agent itself.
        # ---------------------------------------------------------------

        if event.source == VOICE_AGENT_SOURCE:
            return

        # ---------------------------------------------------------------
        # Lifecycle events belong to VoiceLifecycleSubscriber.
        # ---------------------------------------------------------------

        if event.event in VOICE_LIFECYCLE_EVENTS:
            return

        # ---------------------------------------------------------------
        # Route runtime event to the active voice session.
        # ---------------------------------------------------------------

        delivered = await self._registry.dispatch(
            event,
        )

        if delivered:
            return

        logger.debug(
            "No active voice session for runtime event: "
            "event=%s correlation_id=%s",
            event.event,
            event.correlation_id,
        )


# ---------------------------------------------------------------------------
# Voice agent runtime event subscriber
# ---------------------------------------------------------------------------


class VoiceAgentEventSubscriber:
    """
    Subscribes the LiveKit worker to runtime application events.

    This subscriber is responsible only for events that should reach
    an already-running AgentSession.

    Lifecycle events are handled by VoiceLifecycleSubscriber instead.
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
        """Start listening for runtime application events."""

        if (
            self._task is not None
            and not self._task.done()
        ):
            return self._task

        self._task = asyncio.create_task(
            self._run(),
            name="voice-agent-event-subscriber",
        )

        logger.info(
            "Voice agent runtime event subscriber started.",
        )

        return self._task

    async def _run(self) -> None:
        try:
            async for event in self._event_bus.subscribe():

                # -------------------------------------------------------
                # Lifecycle events are handled separately.
                # -------------------------------------------------------

                if event.event in VOICE_LIFECYCLE_EVENTS:
                    continue

                # -------------------------------------------------------
                # Forward runtime events to the router.
                # -------------------------------------------------------

                await self._handle_event(
                    event,
                )

        except asyncio.CancelledError:
            logger.debug(
                "Voice agent runtime event subscriber stopped.",
            )
            raise

        except Exception:
            logger.exception(
                "Voice agent runtime event subscriber "
                "stopped unexpectedly.",
            )

    async def _handle_event(
        self,
        event: ApplicationEvent,
    ) -> None:
        try:
            await self._handler(
                event,
            )

        except Exception:
            logger.exception(
                "Failed to handle voice runtime event: %s",
                event.event,
            )

    async def close(self) -> None:
        """Stop the runtime event subscriber."""

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
            "Voice agent runtime event subscriber closed.",
        )
