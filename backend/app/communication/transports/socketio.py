from __future__ import annotations

from typing import Any

import socketio


class SocketIOTransport:
    """Socket.IO transport for frontend communication."""

    def __init__(
        self,
        sio: socketio.AsyncServer | None = None,
    ) -> None:
        self.sio = sio or socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins="*",
            logger=False,
            engineio_logger=False,
            ping_timeout=1800,
            ping_interval=25,
        )

    async def emit(
        self,
        event: str,
        sid: str,
        payload: dict[str, Any],
    ) -> None:
        """Emit an event to a specific Socket.IO connection."""

        await self.sio.emit(
            event,
            payload,
            to=sid,
        )
