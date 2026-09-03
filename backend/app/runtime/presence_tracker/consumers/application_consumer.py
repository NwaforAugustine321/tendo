
from __future__ import annotations

from collections.abc import Awaitable, Callable


class ApplicationPresenceConsumer:

    def __init__(
        self,
        *,
        callback: Callable[
            [str, int],
            Awaitable[None],
        ],
    ) -> None:
        self._callback = callback

    async def send(
        self,
        *,
        text: str,
        generation: int,
    ) -> None:

        await self._callback(
            text,
            generation,
        )
