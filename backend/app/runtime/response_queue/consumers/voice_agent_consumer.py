from __future__ import annotations

from typing import Any

from app.runtime.response_queue.interface import (
    ResponseConsumer,
)
from ..interface import Kind


class VoiceAgentResponseConsumer(ResponseConsumer):

    def __init__(
        self,
        *,
        session: Any,
    ) -> None:
        self._session = session
        self._speech_handle: Any | None = None

    async def send(
        self,
        *,
        text: str,
        kind: str,
        sequence: int,
    ) -> None:
        self._speech_handle = None

        # Speech must remain interruptible so that a real response
        # can take over immediately when it arrives.
        if kind == Kind.RESPONSE:
            self._speech_handle = self._session.say(
                text,
                allow_interruptions=True,
            )

    async def interrupt(self) -> None:
        handle = self._speech_handle

        if handle is None:
            return

        self._speech_handle = None

        try:
            handle.interrupt()
        except Exception:
            return

    @property
    def speech_handle(self) -> Any | None:
        return self._speech_handle
