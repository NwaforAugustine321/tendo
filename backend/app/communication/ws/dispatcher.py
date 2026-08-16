from __future__ import annotations

from typing import Any

from ..interfaces import SocketConnectionStore
from ..transports.socketio import SocketIOTransport


class SocketDispatcher:
    """Dispatches messages to Socket.IO connections."""

    def __init__(
        self,
        *,
        connection_store: SocketConnectionStore,
        transport: SocketIOTransport,
    ) -> None:
        self._connection_store = connection_store
        self._transport = transport

    async def emit_to_sid(
        self,
        *,
        sid: str,
        event: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Emit an event directly to one Socket.IO connection.

        This is used when the caller already knows the active SID,
        for example when returning a validation error to the
        connection that sent a message.
        """

        if not sid:
            return

        await self._transport.emit(
            event,
            sid,
            payload,
        )

    async def emit_to_user(
        self,
        *,
        user_id: str,
        event: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Emit an event to all active Socket.IO connections
        belonging to a user.
        """

        if not user_id:
            return

        sids = await self._connection_store.get_sockets(
            user_id=user_id,
        )

        if not sids:
            return

        for sid in sids:
            try:
                await self._transport.emit(
                    event,
                    sid,
                    payload,
                )

            except Exception:
                # The SID may have disconnected after Redis returned
                # the active connection list.
                #
                # Remove it from the connection store so subsequent
                # dispatches do not continue targeting a stale SID.
                await self._connection_store.remove_socket(
                    user_id=user_id,
                    sid=sid,
                )
