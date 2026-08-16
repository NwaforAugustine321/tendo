"""Voice session service — business logic for LiveKit voice rooms."""

from __future__ import annotations

import logging
from typing import Any

from livekit.api import LiveKitAPI
from livekit.protocol.room import CreateRoomRequest

from app.communication.events import ApplicationEvent
from app.db.tools.sessions import (
    find_active_session,
    insert_session,
)
from app.config.settings import settings

logger = logging.getLogger(__name__)


class VoiceService:
    """Encapsulates voice session business logic."""

    async def resolve_session(
        self,
        *,
        business_id: str,
        user_id: str,
        session_id: str,
    ) -> str:
        """
        Resolve an existing voice session or create a new one.

        If a session ID is supplied, it is returned unchanged.
        Otherwise an active session is reused when available.
        """

        if session_id:
            return session_id

        existing = await find_active_session(
            business_id,
            user_id,
        )

        if existing:
            return existing["id"]

        new_session = await insert_session(
            business_id,
            user_id,
            title="Voice Session",
        )

        return new_session["id"]

    async def ensure_room(
        self,
        *,
        room_name: str,
        metadata: str,
    ) -> None:
        """
        Ensure that the LiveKit room exists.

        This method only manages the LiveKit room.

        Agent dispatch is handled separately by the application
        EventBus lifecycle subscriber.
        """

        async with LiveKitAPI(
            url=settings.livekit_url,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        ) as api:

            try:
                await api.room.create_room(
                    CreateRoomRequest(
                        name=room_name,
                        metadata=metadata,
                        empty_timeout=300,
                        departure_timeout=30,
                        max_participants=2,
                    ),
                )

                logger.info(
                    "LiveKit voice room created: room=%s",
                    room_name,
                )

            except Exception as exc:
                # A room can already exist because of:
                #
                # - another browser tab
                # - reconnect
                # - repeated start request
                #
                # In that case the existing room can be reused.
                logger.debug(
                    "LiveKit room already exists or could not "
                    "be created: room=%s error=%s",
                    room_name,
                    exc,
                )

    async def request_session(
        self,
        *,
        event_bus: Any,
        payload: dict[str, Any],
    ) -> None:
        """
        Publish a voice-session lifecycle request.

        The FastAPI voice lifecycle subscriber receives this event
        and performs the LiveKit agent dispatch.

        This service does not dispatch the agent directly.
        """

        session_id = payload.get("session_id", "")

        event = ApplicationEvent(
            event="voice.session.requested",
            source="voice-api",
            correlation_id=session_id,
            data=payload,
        )

        await event_bus.publish(
            event,
        )

        logger.info(
            "Voice session requested: payload=%s",
            payload,
        )


voice_service = VoiceService()
