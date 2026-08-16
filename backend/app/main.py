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
from app.communication.provider import EventBusProvider
from app.communication.setup import (
    create_application_event_manager,
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

import app.communication.ws.chat_handler


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


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    """
    Initialize and shut down application-wide resources.

    main.py is responsible only for application composition.

    Event handlers and subscribers are created by the communication
    setup layer.
    """

    from app.scheduler import (
        start_scheduler,
        stop_scheduler,
    )

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

    event_manager = (
        create_application_event_manager(
            event_bus,
        )
    )

    try:

        start_scheduler()

        event_manager.start()

        app.state.event_bus_provider = (
            event_bus_provider
        )

        app.state.event_bus = (
            event_bus
        )

        app.state.event_manager = (
            event_manager
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

        try:
            await event_manager.close()

        except Exception:
            logger.exception(
                "Failed to close application event manager.",
            )

        try:
            await event_bus.close()

        except Exception:
            logger.exception(
                "Failed to close application EventBus.",
            )

        finally:
            clear_event_bus()

        try:
            stop_scheduler()

        except Exception:
            logger.exception(
                "Failed to stop scheduler.",
            )

        logger.info(
            "Application shutdown — connections closed",
        )


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
