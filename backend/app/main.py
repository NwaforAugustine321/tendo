"""Application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.communication.voice import handle_session
from app.models.event import UnifiedUserEvent
from app.routes.auth import router as auth_router
from app.routes.business import router as business_router
from app.routes.upload import router as upload_router
from app.routes.records import router as records_router
from app.routes.conversations import router as conversations_router
from app.routes.snapshot import router as snapshot_router
from app.routes.integrations import router as integrations_router
from app.routes.voice import router as voice_router
from app.lib.errors import register_error_handlers

# Socket.IO for real-time events (voice handler disabled)
import socketio
from app.ws.socketio_server import sio
import app.ws.chat_handler  # noqa: F401 — registers Socket.IO chat events
# import app.ws.voice_handler  # Voice handler disabled for now

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.graph.workflow import init_graph
    from app.scheduler import start_scheduler, stop_scheduler

    try:
        await init_graph()
        start_scheduler()
        logger.info("Application ready")
    except Exception as e:
        logger.critical("STARTUP FAILED: %s", e)
        raise

    yield

    stop_scheduler()
    logger.info("Application shutdown — connections closed")


app = FastAPI(title="Tendo", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tribute-detected-cheese-combining.trycloudflare.com","http://localhost:5173" ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router,prefix="/api")
app.include_router(business_router,prefix="/api")
app.include_router(upload_router,prefix="/api")
app.include_router(records_router,prefix="/api")
app.include_router(conversations_router,prefix="/api")
app.include_router(snapshot_router,prefix="/api")
app.include_router(integrations_router,prefix="/api")
app.include_router(voice_router,prefix="/api")
register_error_handlers(app)

# Socket.IO mounted for real-time events (voice handler not loaded)
asgi_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path='/ws/session')


@app.get("/")
async def health():
    return {"status": "ok", "service": "tendo"}


@app.post("/api/events")
async def receive_event(event: UnifiedUserEvent):
    """Unified event ingress — accepts all user interactions."""
    return {"event_id": event.event_id, "status": "accepted"}
