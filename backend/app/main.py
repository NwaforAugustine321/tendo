from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.models.event import UnifiedUserEvent

app = FastAPI(title="Tendo", version="0.1.0", description="AI Business Operating System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "tendo"}


@app.post("/events")
async def receive_event(event: UnifiedUserEvent):
    """Unified event ingress — accepts all user interactions regardless of channel."""
    # TODO: dispatch to LangGraph workflow
    return {"event_id": event.event_id, "status": "accepted"}


@app.get("/webhook/whatsapp")
async def whatsapp_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """Meta webhook verification — echo the challenge token."""
    if hub_mode == "subscribe" and hub_challenge:
        return PlainTextResponse(content=hub_challenge)
    return PlainTextResponse(content="", status_code=403)


@app.post("/webhook/whatsapp")
async def whatsapp_receive(payload: dict):
    """Receive WhatsApp messages — normalize to UnifiedUserEvent and process."""
    # TODO: normalize payload → UnifiedUserEvent → dispatch
    return {"status": "received"}
