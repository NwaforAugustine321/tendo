from __future__ import annotations
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


EmitFn = Callable[
    [str, dict[str, Any]],
    Awaitable[None],
]


class EmitForwarder:
    """

    Forwards  events to any client transport such as
    Socket.IO, WebSocket, SSE, or another event system.
    """

    def __init__(
        self,
        emit_fn: EmitFn | None = None,
    ) -> None:
        self._emit_fn = emit_fn

    async def emit(
        self,
        event: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """
        Emit an event to the configured transport.
        """

        if self._emit_fn is None:
            return

        payload = {
            "type": event,
            "data": data or {},
        }

        try:
            await self._emit_fn(
                event,
                payload,
            )

        except Exception:
            logger.debug(
                "Failed to emit event: %s",
                event,
                exc_info=True,
            )
