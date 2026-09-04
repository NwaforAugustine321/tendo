
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from livekit import rtc

from ..webhooks.contracts import WebhookEvent

from ..webhooks.handlers.voice_agent_handler import VoiceCommandHandlers
from livekit.agents import (
    JobContext
)

logger = logging.getLogger(__name__)


class VoiceCommandReceiver:

    _TOPIC = "voice.webhook"

    def __init__(
        self,
        *,
        room: rtc.Room,
        user_id: str,
        speak: Callable[[str], Awaitable[None]],
        ctx: JobContext
    ) -> None:

        self._room = room
        self._user_id = user_id
        self._handler = VoiceCommandHandlers(
            speak=speak,
        )
        self._registered = False
        self._background_tasks: set[asyncio.Task] = set()

    def register(self) -> None:

        if self._registered:
            return

        @self._room.on("data_received")
        def on_data_received(
            data: rtc.DataPacket,
        ) -> None:

            print(
                "topic>>>",
                self._TOPIC,
                "data>>>",
                data,
                flush=True,
            )

            if data.topic != self._TOPIC:
                return

            task = asyncio.create_task(self._handle(data))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        print('register successfully here>>>', flush=True)
        self._registered = True

    async def _handle(
        self,
        data: rtc.DataPacket,
    ) -> None:

        print('command receiver doing it thing >>>',  data)

        try:

            event = WebhookEvent.model_validate_json(
                data.data,
            )

        except Exception:

            logger.exception(
                "Failed to decode LiveKit voice command."
            )

            return

        user_id = event.payload.get(
            "user_id",
        )

        if user_id != self._user_id:

            logger.warning(
                "Ignoring voice command for another user: "
                "expected=%s received=%s",
                self._user_id,
                user_id,
            )

            return

        try:

            await self._handler.handle(
                event=event,
            )

        except Exception:

            logger.exception(
                "Failed to handle voice command: "
                "type=%s event_id=%s request_id=%s",
                event.type,
                event.event_id,
                event.request_id,
            )
