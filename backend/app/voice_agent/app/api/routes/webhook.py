
from __future__ import annotations

from fastapi import APIRouter

from app.webhooks.contracts import WebhookEvent
from app.webhooks.dispatcher import WebhookDispatcher


router = APIRouter(
    prefix="/webhooks",
)


dispatcher: WebhookDispatcher | None = None


def configure(
    *,
    webhook_dispatcher: WebhookDispatcher,
) -> None:

    global dispatcher

    dispatcher = webhook_dispatcher


@router.post("/webhook")
async def webhook(
    event: WebhookEvent,
) -> None:

    if dispatcher is None:
        raise RuntimeError(
            "Webhook router has not been configured."
        )

    await dispatcher.dispatch(
        event,
    )
