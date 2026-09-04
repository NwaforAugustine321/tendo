from __future__ import annotations

import logging

from livekit import api

from app.config import settings
from ...webhooks.contracts import WebhookEvent


logger = logging.getLogger(__name__)


class LiveKitWebhookTransport:
    _TOPIC = "voice.webhook"

    def __init__(self) -> None:
        self._client: api.LiveKitAPI | None = None

    async def start(self) -> None:
        if self._client is not None:
            return

        self._client = api.LiveKitAPI(
            url=settings.livekit_url,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )

    async def close(self) -> None:
        if self._client is None:
            return

        try:
            await self._client.aclose()
        except Exception:
            logger.exception(
                "Failed to close LiveKit webhook transport."
            )
        finally:
            self._client = None

    async def send(
        self,
        *,
        event: WebhookEvent,
    ) -> None:
        print('trasporter doing it thing >>>', event)
        if self._client is None:
            logger.warning(
                "LiveKit webhook transport is not started: "
                "type=%s event_id=%s request_id=%s",
                event.type,
                event.event_id,
                event.request_id,
            )
            return

        room_name = event.payload.get("room_name")
        user_id = event.payload.get("user_id")

        if not isinstance(room_name, str) or not room_name:
            logger.error(
                "LiveKit webhook event is missing payload.room_name: "
                "type=%s event_id=%s request_id=%s",
                event.type,
                event.event_id,
                event.request_id,
            )
            return

        if not isinstance(user_id, str) or not user_id:
            logger.error(
                "LiveKit webhook event is missing payload.user_id: "
                "type=%s event_id=%s request_id=%s",
                event.type,
                event.event_id,
                event.request_id,
            )
            return

        try:
            await self._client.room.send_data(
                api.SendDataRequest(
                    room=room_name,
                    data=event.model_dump_json().encode("utf-8"),
                    kind=api.proto_room.DataPacket.Kind.RELIABLE,
                    destination_identities=[user_id],
                    topic=self._TOPIC,
                )
            )

        except Exception:
            logger.exception(
                "Failed to send webhook event through LiveKit: "
                "room=%s user_id=%s type=%s "
                "event_id=%s request_id=%s",
                room_name,
                user_id,
                event.type,
                event.event_id,
                event.request_id,
            )
            return

        logger.debug(
            "Webhook event sent through LiveKit: "
            "room=%s user_id=%s type=%s "
            "event_id=%s request_id=%s",
            room_name,
            user_id,
            event.type,
            event.event_id,
            event.request_id,
        )
