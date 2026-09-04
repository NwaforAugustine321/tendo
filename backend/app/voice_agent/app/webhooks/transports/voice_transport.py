
from __future__ import annotations

from livekit import api

from app.config import settings
from ...webhooks.contracts import WebhookEvent


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

        await self._client.aclose()
        self._client = None

    async def send(
        self,
        *,
        event: WebhookEvent,
    ) -> None:
        if self._client is None:
            raise RuntimeError(
                "LiveKitWebhookTransport has not been started."
            )

        room_name = event.payload.get("room_name")
        user_id = event.payload.get("user_id")

        if not isinstance(room_name, str) or not room_name:
            raise ValueError(
                "Webhook event is missing payload.room_name."
            )

        if not isinstance(user_id, str) or not user_id:
            raise ValueError(
                "Webhook event is missing payload.user_id."
            )

        await self._client.room.send_data(
            api.SendDataRequest(
                room=room_name,
                data=event.model_dump_json().encode("utf-8"),
                kind=api.proto_room.DataPacket.Kind.RELIABLE,
                destination_identities=[user_id],
                topic=self._TOPIC,
            )
        )
