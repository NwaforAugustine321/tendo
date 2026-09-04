from __future__ import annotations
from collections.abc import Awaitable, Callable
from app.runtime.response_queue.interface import (
    ResponseConsumer,
)
from ..interface import Kind


class VoiceAgentResponseConsumer(ResponseConsumer):

    def __init__(
        self,
        *,
        callback: Callable[
            [str, str, int],
            Awaitable[None],
        ],
    ) -> None:

        self._callback = callback

    async def send(
        self,
        *,
        text: str,
        kind: str,
        sequence: int,
    ) -> None:

        if kind not in {
            Kind.PRESENCE_STATE,
            Kind.RESPONSE,
        }:
            return

        await self._callback(
            text,
            kind,
            sequence,
        )

    async def interrupt(self) -> None:
        return

    @property
    def speech_handle(self):
        return None
