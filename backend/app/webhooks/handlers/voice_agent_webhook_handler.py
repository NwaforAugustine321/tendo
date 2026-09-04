
from __future__ import annotations

import logging

from app.planner.planner import Planner
from ..client import WebhookClientInterface
from ..contracts import WebhookEvent
from ..contracts import (
    WebhookType,
    HOOKS
)


logger = logging.getLogger(__name__)


class VoiceAgentWebHookHandler:

    def __init__(
        self,
        *,
        webhook_client: WebhookClientInterface,
    ) -> None:

        self._webhook_client = webhook_client

    async def handle(
        self,
        event: WebhookEvent,
    ) -> None:

        payload = event.payload

        user_message = payload.get(
            "text",
        )

        if not isinstance(user_message, str) or not user_message.strip():
            await self._send_response(
                event=event,
                text="I didn't catch that. Could you repeat?",
            )
            return

        session = {
            **payload
        }

        planner = Planner(
            session=session,
        )

        response = await planner.run(
            user_message=user_message.strip(),
        )

        if not response:
            return

        await self._send_response(
            event=event,
            text=response,
        )

    async def _send_response(
        self,
        *,
        event: WebhookEvent,
        text: str,
    ) -> None:

        payload = event.payload

        response_event = WebhookEvent(
            type=WebhookType.VOICE_RESPONSE,
            event_id=event.event_id,
            request_id=event.request_id,
            payload={

                **payload,
                "text": text,

            },
        )

        await self._webhook_client.send(
            hook=HOOKS.VOICE_AGENT,
            event=response_event,
        )
