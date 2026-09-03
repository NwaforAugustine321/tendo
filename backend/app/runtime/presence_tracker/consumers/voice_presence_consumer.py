
from __future__ import annotations

from typing import Any

from app.runtime.presence_tracker.interface import PresenceConsumer


class LiveKitPresenceConsumer(PresenceConsumer):

    def __init__(
        self,
        *,
        session: Any,
    ) -> None:
        self._session = session

    async def send(
        self,
        *,
        text: str,
        generation: int,
    ) -> None:

        await self._session.say(
            text,
        )
