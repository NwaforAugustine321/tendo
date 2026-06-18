"""Application entrypoint."""

import logging

from fastapi import FastAPI, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.communication.voice import handle_session
from app.models.event import UnifiedUserEvent
from app.routes.auth import router as auth_router
from app.routes.business import router as business_router
from app.lib.errors import register_error_handlers

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Tendo", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(business_router)
register_error_handlers(app)


@app.on_event("startup")
async def startup_memory_system():
    """Initialize memory system tables on startup."""
    try:
        from app.memory import ensure_checkpointer, ensure_store
        await ensure_checkpointer()
        await ensure_store()
        logger.info("Memory system initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize memory system: %s", e)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "tendo"}


@app.post("/events")
async def receive_event(event: UnifiedUserEvent):
    """Unified event ingress — accepts all user interactions."""
    # TODO: dispatch to workflow
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
    # TODO: normalize payload → event → dispatch
    return {"status": "received"}


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """Real-time voice-to-voice WebSocket."""
    await handle_session(websocket)
