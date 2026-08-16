"""Application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.communication.config import EventBusConfig
from app.communication.event_bus import (
    clear_event_bus,
    set_event_bus,
)
from app.communication.events import ApplicationEvent
from app.communication.provider import EventBusProvider
from app.communication.subscribers.subscriber import (
    ApplicationEventSubscriber,
)
from app.communication.ws.server import sio
from app.config import settings
from app.lib.errors import register_error_handlers
from app.models.event import UnifiedUserEvent
from app.routes.auth import router as auth_router
from app.routes.business import router as business_router
from app.routes.conversations import router as conversations_router
from app.routes.integrations import router as integrations_router
from app.routes.records import router as records_router
from app.routes.snapshot import router as snapshot_router
from app.routes.upload import router as upload_router
from app.routes.voice import router as voice_router
from app.voice_agent.lifecycle import (
    voice_lifecycle_service,
)
from app.voice_agent.subscriber import (
    VoiceLifecycleSubscriber,
)

import app.communication.ws.chat_handler


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)

logging.getLogger(
    "httpx",
).setLevel(
    logging.WARNING,
)

logging.getLogger(
    "apscheduler",
).setLevel(
    logging.WARNING,
)

logger = logging.getLogger(
    __name__,
)


# ---------------------------------------------------------------------------
# Application event handler
# ---------------------------------------------------------------------------


async def handle_application_event(
    event: ApplicationEvent,
) -> None:
    """
    Forward application events to the appropriate frontend
    Socket.IO room.

    Uses business_id from event data as the room target when available,
    falling back to correlation_id (session_id).
    """

    if not event.correlation_id:
        logger.debug(
            "Ignoring application event without correlation_id: %s",
            event.event,
        )
        return

    # Determine the room: prefer business_id (client always joins that room),
    # fall back to correlation_id (session_id).
    room = event.correlation_id
    if isinstance(event.data, dict):
        business_id = event.data.get("business_id", "")
        if business_id:
            room = business_id

    try:
        await sio.emit(
            event.event,
            event.to_dict(),
            room=room,
        )

        logger.debug(
            "Forwarded application event: "
            "event=%s room=%s",
            event.event,
            room,
        )

    except Exception:
        logger.exception(
            "Failed to forward application event: %s",
            event.event,
        )


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    """
    Initialize and shut down application-wide resources.

    Resources created here are shared by the FastAPI process:

        EventBus
            ├── ApplicationEventSubscriber
            │       └── Frontend Socket.IO events
            │
            └── VoiceLifecycleSubscriber
                    └── LiveKit agent lifecycle

    The EventBus is also registered through the general application
    EventBus accessor so any application component can use:

        get_event_bus()
    """

    from app.scheduler import (
        start_scheduler,
        stop_scheduler,
    )

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

    # -----------------------------------------------------------------------
    # Register process-local EventBus
    # -----------------------------------------------------------------------

    # This makes the EventBus available to application code through:
    #
    #     from app.communication.event_bus import get_event_bus
    #
    # The EventBus itself is still backed by Redis and is not shared
    # as a Python object between processes.
    set_event_bus(
        event_bus,
    )

    # -----------------------------------------------------------------------
    # Frontend application-event subscriber
    # -----------------------------------------------------------------------

    event_subscriber = ApplicationEventSubscriber(
        event_bus=event_bus,
        handler=handle_application_event,
    )

    # -----------------------------------------------------------------------
    # Voice lifecycle subscriber
    # -----------------------------------------------------------------------

    voice_lifecycle_subscriber = (
        VoiceLifecycleSubscriber(
            event_bus=event_bus,
            service=voice_lifecycle_service,
        )
    )

    try:
        # -------------------------------------------------------------------
        # Start application services
        # -------------------------------------------------------------------

        start_scheduler()

        event_subscriber.start()

        voice_lifecycle_subscriber.start()

        # -------------------------------------------------------------------
        # Expose resources through FastAPI app state
        # -------------------------------------------------------------------

        # Keep these available for components that explicitly use
        # app.state, although normal application code should prefer
        # get_event_bus().
        app.state.event_bus_provider = (
            event_bus_provider
        )

        app.state.event_bus = (
            event_bus
        )

        app.state.event_subscriber = (
            event_subscriber
        )

        app.state.voice_lifecycle_subscriber = (
            voice_lifecycle_subscriber
        )

        logger.info(
            "Application ready",
        )

        yield

    except Exception as exc:
        logger.critical(
            "STARTUP FAILED: %s",
            exc,
            exc_info=True,
        )

        raise

    finally:
        # -------------------------------------------------------------------
        # Shutdown lifecycle subscriber
        # -------------------------------------------------------------------

        try:
            await voice_lifecycle_subscriber.close()

        except Exception:
            logger.exception(
                "Failed to close voice lifecycle subscriber.",
            )

        # -------------------------------------------------------------------
        # Shutdown application event subscriber
        # -------------------------------------------------------------------

        try:
            await event_subscriber.close()

        except Exception:
            logger.exception(
                "Failed to close application event subscriber.",
            )

        # -------------------------------------------------------------------
        # Close EventBus
        # -------------------------------------------------------------------

        try:
            await event_bus.close()

        except Exception:
            logger.exception(
                "Failed to close application EventBus.",
            )

        finally:
            # Remove the process-local reference after the EventBus
            # has been closed.
            clear_event_bus()

        # -------------------------------------------------------------------
        # Stop scheduler
        # -------------------------------------------------------------------

        try:
            stop_scheduler()

        except Exception:
            logger.exception(
                "Failed to stop scheduler.",
            )

        logger.info(
            "Application shutdown — connections closed",
        )


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Tendo",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://journal-points-bundle-income.trycloudflare.com",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

app.include_router(
    auth_router,
    prefix="/api",
)

app.include_router(
    business_router,
    prefix="/api",
)

app.include_router(
    upload_router,
    prefix="/api",
)

app.include_router(
    records_router,
    prefix="/api",
)

app.include_router(
    conversations_router,
    prefix="/api",
)

app.include_router(
    snapshot_router,
    prefix="/api",
)

app.include_router(
    integrations_router,
    prefix="/api",
)

app.include_router(
    voice_router,
    prefix="/api",
)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

register_error_handlers(
    app,
)


# ---------------------------------------------------------------------------
# Socket.IO ASGI application
# ---------------------------------------------------------------------------

asgi_app = socketio.ASGIApp(
    sio,
    other_asgi_app=app,
    socketio_path="/ws/session",
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/")
async def health():
    """Application health endpoint."""

    return {
        "status": "ok",
        "service": "tendo",
    }


# ---------------------------------------------------------------------------
# Unified event ingress
# ---------------------------------------------------------------------------


@app.post(
    "/api/events",
)
async def receive_event(
    event: UnifiedUserEvent,
):
    """
    Unified event ingress.

    This endpoint accepts user/application events. Actual event
    processing is handled by the corresponding EventBus subscribers.
    """

    return {
        "event_id": event.event_id,
        "status": "accepted",
    }
