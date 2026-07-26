"""Application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.communication.voice import handle_session
from app.models.event import UnifiedUserEvent
from app.routes.auth import router as auth_router
from app.routes.business import router as business_router
from app.routes.upload import router as upload_router
from app.routes.records import router as records_router
from app.routes.conversations import router as conversations_router
from app.routes.snapshot import router as snapshot_router
from app.lib.errors import register_error_handlers

import socketio
from app.ws.socketio_server import sio
import app.ws.voice_handler  # noqa: F401 — registers Socket.IO event handlers

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.graph.workflow import init_graph
    from app.scheduler import start_scheduler, stop_scheduler
    from app.record_knowledge.record_agent import _get_record_storage

    try:
        await init_graph()
        start_scheduler()
        _get_record_storage()
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
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(business_router)
app.include_router(upload_router)
app.include_router(records_router)
app.include_router(conversations_router)
app.include_router(snapshot_router)
register_error_handlers(app)

# Mount Socket.IO on /ws/voice path
asgi_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path='/ws/voice')


@app.get("/health")
async def health():
    return {"status": "ok", "service": "tendo"}


@app.post("/events")
async def receive_event(event: UnifiedUserEvent):
    """Unified event ingress — accepts all user interactions."""
    return {"event_id": event.event_id, "status": "accepted"}


@app.get("/webhook/whatsapp")
async def whatsapp_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """Webhook verification — echo the challenge token."""
    if hub_mode == "subscribe" and hub_challenge:
        return PlainTextResponse(content=hub_challenge)
    return PlainTextResponse(content="", status_code=403)


@app.post("/webhook/whatsapp")
async def whatsapp_receive(payload: dict):
    """Receive messages — normalize and process."""
    return {"status": "received"}


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """Real-time voice-to-voice WebSocket."""
    # await handle_session(websocket)
    pass
