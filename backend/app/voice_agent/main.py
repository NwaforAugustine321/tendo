
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.routes import router
from app.api.routes.webhook import (
    configure as configure_webhook_router,
)
from app.api.routes.webhook import router as webhook_router
from app.agent.worker import server
from app.webhooks.dispatcher import WebhookDispatcher
from app.webhooks.transports.voice_transport import (
    LiveKitWebhookTransport,
)


livekit_transport = LiveKitWebhookTransport()

webhook_dispatcher = WebhookDispatcher(
    handlers={
        "voice.presence": livekit_transport.send,
        "voice.response": livekit_transport.send,
    },
)

configure_webhook_router(
    webhook_dispatcher=webhook_dispatcher,
)


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    await livekit_transport.start()

    agent_task = asyncio.create_task(
        server.run(),
    )

    try:
        yield

    finally:
        server.shutdown()

        await agent_task

        await livekit_transport.close()


app = FastAPI(
    title="Voice Agent Service",
    lifespan=lifespan,
)

app.include_router(
    router,
)

app.include_router(
    webhook_router,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
    }
