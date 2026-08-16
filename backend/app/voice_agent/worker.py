from __future__ import annotations

import logging
import os
import sys

from livekit.agents import (
    AgentServer,
    JobContext,
    JobProcess,
    cli,
)

from app.communication.config import EventBusConfig
from app.communication.event_bus import set_event_bus
from app.communication.provider import EventBusProvider
from app.config import settings

from .events import (
    VoiceAgentEventRouter,
    VoiceAgentEventSubscriber,
    VoiceSessionRegistry,
)
from .handlers import VoiceSessionHandlers
from .metadata import VoiceSessionMetadataParser
from .model import InvalidVoiceSessionMetadata
from .resources import VoiceResources
from .session import VoiceSessionService


os.environ.setdefault(
    "LIVEKIT_URL",
    settings.livekit_url,
)

os.environ.setdefault(
    "LIVEKIT_API_KEY",
    settings.livekit_api_key,
)

os.environ.setdefault(
    "LIVEKIT_API_SECRET",
    settings.livekit_api_secret,
)

os.environ.setdefault(
    "NVIDIA_API_KEY",
    settings.nvidia_api_key,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(
    "voice-worker",
)

logging.getLogger(
    "livekit.agents",
).setLevel(
    logging.WARNING,
)

logging.getLogger(
    "livekit",
).setLevel(
    logging.WARNING,
)

logging.getLogger(
    "asyncio",
).setLevel(
    logging.CRITICAL,
)


sys.path.insert(
    0,
    os.path.dirname(__file__),
)


# ---------------------------------------------------------------------------
# LiveKit server
# ---------------------------------------------------------------------------

server = AgentServer(
    num_idle_processes=2,
)


# ---------------------------------------------------------------------------
# Process initialization
# ---------------------------------------------------------------------------


def prewarm(
    proc: JobProcess,
) -> None:
    """
    Initialize resources owned by a LiveKit worker process.

    No asynchronous tasks are started here.

    The lifecycle event that dispatches the LiveKit agent is handled
    by the FastAPI application EventBus lifecycle.

    This worker only prepares resources required once LiveKit starts
    an actual voice session.
    """

    logger.info(
        "Initializing voice worker process: pid=%s",
        os.getpid(),
    )

    # -----------------------------------------------------------------------
    # Voice resources
    # -----------------------------------------------------------------------

    resources = VoiceResources()

    metadata_parser = VoiceSessionMetadataParser()

    # -----------------------------------------------------------------------
    # EventBus
    # -----------------------------------------------------------------------

    event_bus_provider = EventBusProvider(
        EventBusConfig(
            channel="application.events",
            options={
                "url": settings.redis_url,
            },
        ),
    )

    event_bus = event_bus_provider.get()

    # Make the EventBus available via the global accessor so that
    # components like the planner can publish events without needing
    # a direct reference.
    set_event_bus(event_bus)

    # -----------------------------------------------------------------------
    # Voice session registry
    # -----------------------------------------------------------------------

    session_registry = VoiceSessionRegistry()

    # -----------------------------------------------------------------------
    # Runtime event routing
    # -----------------------------------------------------------------------

    event_router = VoiceAgentEventRouter(
        registry=session_registry,
    )

    event_subscriber = VoiceAgentEventSubscriber(
        event_bus=event_bus,
        handler=event_router.handle,
    )

    # -----------------------------------------------------------------------
    # Process state
    # -----------------------------------------------------------------------

    proc.userdata["resources"] = resources

    proc.userdata["metadata_parser"] = (
        metadata_parser
    )

    proc.userdata["event_bus_provider"] = (
        event_bus_provider
    )

    proc.userdata["event_bus"] = (
        event_bus
    )

    proc.userdata["session_registry"] = (
        session_registry
    )

    proc.userdata["event_subscriber"] = (
        event_subscriber
    )

    logger.info(
        "Voice worker process initialized: pid=%s",
        os.getpid(),
    )


server.setup_fnc = prewarm


# ---------------------------------------------------------------------------
# Voice session
# ---------------------------------------------------------------------------


@server.rtc_session(
    agent_name="tendo-voice",
)
async def tendo_session(
    ctx: JobContext,
) -> None:
    """
    Create and run a voice session.

    This function is called by LiveKit after the FastAPI application
    has requested a `tendo-voice` agent dispatch.
    """

    resources: VoiceResources = ctx.proc.userdata[
        "resources"
    ]

    metadata_parser: VoiceSessionMetadataParser = (
        ctx.proc.userdata[
            "metadata_parser"
        ]
    )

    event_bus = ctx.proc.userdata[
        "event_bus"
    ]

    session_registry: VoiceSessionRegistry = (
        ctx.proc.userdata[
            "session_registry"
        ]
    )

    event_subscriber: VoiceAgentEventSubscriber = (
        ctx.proc.userdata[
            "event_subscriber"
        ]
    )

    # -----------------------------------------------------------------------
    # Start application-event subscriber
    # -----------------------------------------------------------------------

    # Safe here because rtc_session executes inside the
    # LiveKit asyncio runtime.
    #
    # This subscriber handles application events destined for
    # the active voice session.
    event_subscriber.start()

    # -----------------------------------------------------------------------
    # Voice resources
    # -----------------------------------------------------------------------

    graph, stt, tts = resources.get()

    # -----------------------------------------------------------------------
    # Session metadata
    # -----------------------------------------------------------------------

    metadata = (
        ctx.job.metadata
        or ctx.room.metadata
    )

    try:
        session_data = metadata_parser.parse(
            metadata,
        )

    except InvalidVoiceSessionMetadata as exc:
        logger.error(
            "[tendo_session] %s",
            exc,
        )

        await ctx.shutdown()
        return

    logger.info(
        "[tendo_session] "
        "metadata_id=%s",
        str(session_data)
    )

    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # -----------------------------------------------------------------------
    # Voice session service
    # -----------------------------------------------------------------------

    session_service = VoiceSessionService(
        event_bus=event_bus,
        registry=session_registry,
        graph=graph,
        stt=stt,
        tts=tts,
    )

    session = await session_service.start(
        ctx=ctx,
        data=session_data,
    )

    VoiceSessionHandlers().register(
        session,
    )

    # -----------------------------------------------------------------------
    # Connect to LiveKit
    # -----------------------------------------------------------------------

    await ctx.connect()

    # -----------------------------------------------------------------------
    # Shutdown
    # -----------------------------------------------------------------------

    async def _shutdown() -> None:
        try:
            await session_service.close(
                session_id=session_data.session_id,
                session=session,
            )

        finally:
            await session_registry.unregister(
                session_data.session_id,
            )

    ctx.add_shutdown_callback(
        _shutdown,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    cli.run_app(
        server,
    )
