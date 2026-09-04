from __future__ import annotations

import logging

from fastapi import APIRouter

from app.webhooks.contracts import WebhookEvent
from app.webhooks.dispatcher import WebhookDispatcher


logger = logging.getLogger(__name__)


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


@router.post("/receiver")
async def webhook(
    event: WebhookEvent,
) -> None:

    if dispatcher is None:
        logger.error(
            "Webhook router has not been configured: "
            "type=%s event_id=%s request_id=%s",
            event.type,
            event.event_id,
            event.request_id,
        )
        return

    await dispatcher.dispatch(
        event=event,
    )
