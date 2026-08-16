from __future__ import annotations

import asyncio
from datetime import timedelta

from app.communication.interfaces import SocketConnectionStore

from .models import SocketConnection


class SocketConnectionRegistry:
    """
    Tracks Socket.IO connection metadata locally and synchronizes
    active connection SIDs with the connection store.
    """

    def __init__(
        self,
        *,
        connection_store: SocketConnectionStore,
        ttl: timedelta = timedelta(minutes=2),
    ) -> None:
        self._connection_store = connection_store
        self._ttl = ttl

        self._connections: dict[
            str,
            SocketConnection,
        ] = {}

        self._lock = asyncio.Lock()

    async def register(
        self,
        connection: SocketConnection,
    ) -> None:
        """
        Register a Socket.IO connection.

        Connection metadata is kept locally while the active SID
        is registered in the shared connection store.
        """

        async with self._lock:
            self._connections[
                connection.sid
            ] = connection

        if connection.user_id:
            await self._connection_store.add_socket(
                user_id=connection.user_id,
                sid=connection.sid,
                ttl=self._ttl,
            )

    async def get(
        self,
        sid: str,
    ) -> SocketConnection | None:
        """Get local connection metadata by Socket.IO SID."""

        async with self._lock:
            return self._connections.get(
                sid,
            )

    async def remove(
        self,
        sid: str,
    ) -> None:
        """
        Remove a Socket.IO connection from the local registry
        and the active connection store.
        """

        async with self._lock:
            connection = self._connections.pop(
                sid,
                None,
            )

        if connection is None:
            return

        if connection.user_id:
            await self._connection_store.remove_socket(
                user_id=connection.user_id,
                sid=connection.sid,
            )

    async def refresh(
        self,
        sid: str,
    ) -> bool:
        """Refresh the active connection expiration."""

        return await self._connection_store.refresh_socket(
            sid=sid,
            ttl=self._ttl,
        )

    async def clear(self) -> None:
        """
        Remove all locally tracked connections and invalidate
        their active Redis connection entries.
        """

        async with self._lock:
            connections = list(
                self._connections.values(),
            )

            self._connections.clear()

        for connection in connections:
            if not connection.user_id:
                continue

            await self._connection_store.remove_socket(
                user_id=connection.user_id,
                sid=connection.sid,
            )
