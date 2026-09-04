
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
from app.routes.snaps import router as snaps_router
from app.routes.upload import router as upload_router
from app.routes.voice import router as voice_router
from app.routes.webhooks import (
    router as webhook_router,
)
from app.routes.webhooks import (
    configure as configure_webhook,
)

from app.webhooks.client import (
    WebhookClient,
    WebhookConfig,
)
from app.webhooks.dispatcher import WebhookDispatcher
from app.webhooks.handlers.voice_agent_webhook_handler import VoiceAgentWebHookHandler

import app.communication.ws.chat_handler


# ============================================================================
# Logging
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)

logging.getLogger("httpx").setLevel(
    logging.WARNING,
)

logging.getLogger("apscheduler").setLevel(
    logging.WARNING,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Application lifespan
# ============================================================================


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    """
    Initialize and shut down application-wide resources.

    main.py is responsible only for application composition.

    Background-job infrastructure is created and owned by
    BackgroundJobSystem.

    BackgroundJobSystem owns:

        - BackgroundJobRPC
        - WorkerRegistry
        - BackgroundRunner
        - BackgroundDispatcher
        - BackgroundScheduler

    Communication infrastructure is created and owned by
    the communication setup layer.

    Communication infrastructure includes:

        - EventBus
        - EventManager
        - Event subscribers
    """

    from app.background.factory import (
        create_background_job_system,
    )

    # ------------------------------------------------------------------------
    # EventBus
    # ------------------------------------------------------------------------

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

    # ------------------------------------------------------------------------
    # Application Event Manager
    # ------------------------------------------------------------------------

    event_manager = (
        create_application_event_manager(
            event_bus,
        )
    )

    # ------------------------------------------------------------------------
    # Webhook System
    # ------------------------------------------------------------------------

    webhook_client = WebhookClient(
        hooks={
            "voice.agent": WebhookConfig(
                url="http://localhost:8001/webhooks/webhook",
                secret=settings.webhook_internal_secret,
                timeout=60.0,
            ),
        },
    )

    voice_agent_webhook_handler = VoiceAgentWebHookHandler(
        webhook_client=webhook_client,
    )

    webhook_dispatcher = WebhookDispatcher(
        handlers={
            "voice.transcript": (
                voice_agent_webhook_handler.handle
            ),
        },
        events={
            "voice.transcript",
        },
    )

    configure_webhook(
        webhook_dispatcher=webhook_dispatcher,
    )

    # ------------------------------------------------------------------------
    # Background Job System
    # ------------------------------------------------------------------------

    background_job_system = None

    try:

        await webhook_client.start()

        background_job_system = (
            create_background_job_system()
        )

        # ---------------------------------------------------------------
        # Start background-job infrastructure
        #
        # This starts APScheduler only.
        #
        # APScheduler will independently trigger:
        #
        #     dispatch_once()
        #     recover_once()
        #
        # The runner and RPC layer handle the actual work.
        # ---------------------------------------------------------------

        background_job_system.start()

        # ---------------------------------------------------------------
        # Start application event system
        # ---------------------------------------------------------------

        event_manager.start()

        # ---------------------------------------------------------------
        # Store application-wide resources
        # ---------------------------------------------------------------

        app.state.event_bus_provider = (
            event_bus_provider
        )

        app.state.event_bus = (
            event_bus
        )

        app.state.event_manager = (
            event_manager
        )

        app.state.webhook_client = (
            webhook_client
        )

        app.state.webhook_dispatcher = (
            webhook_dispatcher
        )

        app.state.voice_agent_handler = (
            voice_agent_webhook_handler
        )

        app.state.background_job_system = (
            background_job_system
        )

        # ---------------------------------------------------------------
        # Optional background-job component references
        #
        # These are convenience references for application services
        # that need to enqueue jobs or inspect the infrastructure.
        # ---------------------------------------------------------------

        app.state.background_job_rpc = (
            background_job_system.rpc
        )

        app.state.background_worker_registry = (
            background_job_system.registry
        )

        app.state.background_job_runner = (
            background_job_system.runner
        )

        app.state.background_job_dispatcher = (
            background_job_system.dispatcher
        )

        app.state.background_scheduler = (
            background_job_system.scheduler
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

        # --------------------------------------------------------------------
        # Stop application event manager
        #
        # EventManager is stopped before EventBus is closed.
        # --------------------------------------------------------------------

        try:

            await event_manager.close()

        except Exception:

            logger.exception(
                "Failed to close application event manager.",
            )

        # --------------------------------------------------------------------
        # Stop background-job system
        #
        # This happens before closing shared resources such as
        # Redis/EventBus because background workers may still depend
        # on those resources.
        # --------------------------------------------------------------------

        if background_job_system is not None:

            try:

                await background_job_system.shutdown()

            except Exception:

                logger.exception(
                    "Failed to stop background job system.",
                )

        # --------------------------------------------------------------------
        # Close Webhook Client
        # --------------------------------------------------------------------

        try:

            await webhook_client.close()

        except Exception:

            logger.exception(
                "Failed to close webhook client.",
            )

        # --------------------------------------------------------------------
        # Close EventBus
        # --------------------------------------------------------------------

        try:

            await event_bus.close()

        except Exception:

            logger.exception(
                "Failed to close application EventBus.",
            )

        finally:

            clear_event_bus()

        logger.info(
            "Application shutdown — connections closed",
        )


# ============================================================================
# FastAPI
# ============================================================================

app = FastAPI(
    title="Tendo",
    version="0.1.0",
    lifespan=lifespan,
)


# ============================================================================
# CORS
# ============================================================================

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


# ============================================================================
# Routes
# ============================================================================

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
    snaps_router,
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

app.include_router(
    webhook_router,
)


# ============================================================================
# Error Handlers
# ============================================================================

register_error_handlers(
    app,
)


# ============================================================================
# Socket.IO ASGI Application
# ============================================================================

asgi_app = socketio.ASGIApp(
    sio,
    other_asgi_app=app,
    socketio_path="/ws/session",
)


# ============================================================================
# Health
# ============================================================================


@app.get("/")
async def health():
    """Application health endpoint."""

    return {
        "status": "ok",
        "service": "tendo",
    }


# ============================================================================
# Unified Event Ingress
# ============================================================================


@app.post(
    "/api/events",
)
async def receive_event(
    event: UnifiedUserEvent,
):
    """
    Unified event ingress.

    This endpoint accepts user/melication events.

    Actual event processing is handled by the corresponding
    EventBus subscribers.
    """

    return {
        "event_id": event.event_id,
        "status": "accepted",
    }
