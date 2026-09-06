
from __future__ import annotations

import logging
import asyncio
from app.planner.planner import Planner
from ..client import WebhookClientInterface
from ..contracts import WebhookEvent
from ..contracts import (
    WebhookType,
    HOOKS
)
from app.communication.events import ApplicationEvent
from app.communication.event_bus import get_event_bus
from app.communication.events import EventDelivery

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

        user_id = payload.get(
            "user_id",
        )

        if not isinstance(user_message, str) or not user_message.strip():
            await self._send_response(
                event=event,
                text="I didn't catch that. Could you repeat?",
            )
            return

        payload = {
            "type": "voice.transcript",
            "payload": {
                "message": user_message,
            },
            "user_id": user_id,
        }

        await get_event_bus().publish(
            ApplicationEvent(
                event="voice.transcript",
                source="agent",
                delivery=EventDelivery.APP,
                data=payload,
            ),
        )

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

        asyncio.create_task(
            self._run_background_tasks(
                event=event,
                user_id=user_id,
                response=response,
            ),
        )

    async def _publish_text_message(
        self,
        user_id: str,
        response: str,
    ) -> None:
        payload = {
            "type": "message",
            "payload": {
                "message": response,
            },
            "user_id": user_id,
        }

        await get_event_bus().publish(
            ApplicationEvent(
                event="message",
                source="agent",
                delivery=EventDelivery.APP,
                data=payload,
            ),
        )

    async def _publish_voice_message(
        self,
        event: Any,
        response: str,
    ) -> None:
        await self._send_response(
            event=event,
            text=response,
        )

    async def _run_background_task(
        self,
        task_name: str,
        coroutine,
    ) -> None:
        try:
            await coroutine
        except Exception:
            logger.exception(
                "Message task delivery failed: %s",
                task_name,
            )

    async def _run_background_tasks(
        self,
        event: Any,
        user_id: str,
        response: str,
    ) -> None:
        await asyncio.gather(
            self._run_background_task(
                "publish_text_message",
                self._publish_text_message(
                    user_id=user_id,
                    response=response,
                ),
            ),
            self._run_background_task(
                "publish_voice_message",
                self._publish_voice_message(
                    event=event,
                    response=response,
                ),
            ),
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
