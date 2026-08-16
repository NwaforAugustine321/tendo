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


server = AgentServer(
    num_idle_processes=2,
)


def prewarm(
    proc: JobProcess,
) -> None:
    """Initialize resources owned by a LiveKit worker process."""

    logger.info(
        "Initializing voice worker process: pid=%s",
        os.getpid(),
    )

    resources = VoiceResources()

    metadata_parser = VoiceSessionMetadataParser()

    event_bus_provider = EventBusProvider(
        EventBusConfig(
            channel="application.events",
            options={
                "url": settings.redis_url,
            },
        ),
    )

    event_bus = event_bus_provider.get()

    set_event_bus(
        event_bus,
    )

    session_registry = VoiceSessionRegistry()

    event_router = VoiceAgentEventRouter(
        registry=session_registry,
    )

    event_subscriber = VoiceAgentEventSubscriber(
        event_bus=event_bus,
        handler=event_router.handle,
    )

    proc.userdata["resources"] = resources
    proc.userdata["metadata_parser"] = metadata_parser
    proc.userdata["event_bus_provider"] = event_bus_provider
    proc.userdata["event_bus"] = event_bus
    proc.userdata["session_registry"] = session_registry
    proc.userdata["event_subscriber"] = event_subscriber

    logger.info(
        "Voice worker process initialized: pid=%s",
        os.getpid(),
    )


server.setup_fnc = prewarm


@server.rtc_session(
    agent_name="tendo-voice",
)
async def tendo_session(
    ctx: JobContext,
) -> None:
    """Create and run a voice session."""

    resources: VoiceResources = (
        ctx.proc.userdata[
            "resources"
        ]
    )

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

    event_subscriber.start()

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
            "[tendo_session] Invalid voice session metadata: %s",
            exc,
        )

        await ctx.shutdown()
        return

    logger.info(
        "[tendo_session] Voice session metadata parsed: "
        "room=%s business_id=%s session_id=%s "
        "user_id=%s record_id=%s",
        ctx.room.name,
        session_data.business_id,
        session_data.session_id,
        session_data.user_id,
        session_data.record_id,
    )

    ctx.log_context_fields = {
        "room": ctx.room.name,
        "session_id": session_data.session_id,
        "user_id": session_data.user_id,
        "business_id": session_data.business_id,
    }

    graph, stt, tts = resources.get()

    session_handlers = VoiceSessionHandlers()

    session_service = VoiceSessionService(
        event_bus=event_bus,
        registry=session_registry,
        graph=graph,
        stt=stt,
        tts=tts,
        handlers=session_handlers,
    )

    session = None

    try:
        session = await session_service.start(
            ctx=ctx,
            data=session_data,
            resources=resources,
        )

        logger.info(
            "[tendo_session] Voice session started: "
            "room=%s session_id=%s user_id=%s",
            ctx.room.name,
            session_data.session_id,
            session_data.user_id,
        )

        await ctx.connect()

        logger.info(
            "[tendo_session] Connected to LiveKit: "
            "room=%s session_id=%s",
            ctx.room.name,
            session_data.session_id,
        )

    except Exception:
        logger.exception(
            "[tendo_session] Voice session failed: "
            "room=%s session_id=%s",
            ctx.room.name,
            session_data.session_id,
        )

        if session is not None:
            try:
                await session_service.close(
                    session_id=session_data.session_id,
                    session=session,
                )
            except Exception:
                logger.exception(
                    "[tendo_session] Failed to close failed "
                    "voice session: session_id=%s",
                    session_data.session_id,
                )

        raise

    async def _shutdown() -> None:
        logger.info(
            "[tendo_session] Shutting down voice session: "
            "room=%s session_id=%s",
            ctx.room.name,
            session_data.session_id,
        )

        if session is None:
            return

        try:
            await session_service.close(
                session_id=session_data.session_id,
                session=session,
            )

        except Exception:
            logger.exception(
                "[tendo_session] Failed to close voice session: "
                "session_id=%s",
                session_data.session_id,
            )

        finally:
            await session_registry.unregister(
                session_data.session_id,
            )

    ctx.add_shutdown_callback(
        _shutdown,
    )


if __name__ == "__main__":
    cli.run_app(
        server,
    )
