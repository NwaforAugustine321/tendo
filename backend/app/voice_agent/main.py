from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.routes import router
from app.api.routes.webhook import (
    configure as configure_webhook_router,
)
from app.api.routes.webhook import router as webhook_router
from app.agent.worker import server
from app.webhooks.contracts import WebhookType
from app.webhooks.dispatcher import WebhookDispatcher
from app.webhooks.transports.voice_transport import (
    LiveKitWebhookTransport,
)


livekit_transport = LiveKitWebhookTransport()

webhook_dispatcher = WebhookDispatcher(
    handlers={
        WebhookType.VOICE_PRESENCE: livekit_transport.send,
        WebhookType.VOICE_RESPONSE: livekit_transport.send,
    },
    events={
        WebhookType.VOICE_PRESENCE,
        WebhookType.VOICE_RESPONSE,
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
        name="livekit-agent-server",
    )

    try:
        yield

    finally:
        try:
            try:
                await asyncio.wait_for(
                    server.drain(),
                    timeout=5.0,
                )
            except asyncio.TimeoutError:
                pass
            except Exception:
                pass

            try:
                await server.aclose()
            except Exception:
                pass

            if not agent_task.done():
                try:
                    await asyncio.wait_for(
                        agent_task,
                        timeout=5.0,
                    )
                except asyncio.TimeoutError:
                    agent_task.cancel()

                    try:
                        await agent_task
                    except asyncio.CancelledError:
                        pass
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass

        finally:
            await livekit_transport.close()


app = FastAPI(
    title="Voice Agent Service",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    router,
    prefix="/api",
)

app.include_router(
    webhook_router,
    prefix="/api",
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
    }
