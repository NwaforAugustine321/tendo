from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Protocol

from .events import ApplicationEvent


class EventBus(Protocol):
    """Transport-independent application event bus."""

    async def publish(
        self,
        event: ApplicationEvent,
    ) -> None:
        """Publish an application event."""
        ...

    def subscribe(
        self,
        event: str | None = None,
    ) -> AsyncIterator[ApplicationEvent]:
        """Subscribe to application events."""
        ...

    async def close(self) -> None:
        """Release event bus resources."""
        ...


class EventTransport(Protocol):
    """Low-level transport for serialized application events."""

    async def publish(
        self,
        channel: str,
        payload: str,
    ) -> None:
        """Publish a serialized event payload."""
        ...

    def subscribe(
        self,
        channel: str,
    ) -> AsyncIterator[str]:
        """Subscribe to serialized event payloads."""
        ...

    async def close(self) -> None:
        """Close the transport connection."""
        ...


class SocketConnectionStore(Protocol):
    """
    Stores and resolves active Socket.IO connections.

    Implementations maintain the relationship between a user and
    their currently active Socket.IO connection SIDs.
    """

    async def add_socket(
        self,
        *,
        user_id: str,
        sid: str,
        ttl: timedelta,
    ) -> None:
        """Register an active Socket.IO connection."""
        ...

    async def get_sockets(
        self,
        *,
        user_id: str,
    ) -> list[str]:
        """Return active Socket.IO SIDs for a user."""
        ...

    async def refresh_socket(
        self,
        *,
        sid: str,
        ttl: timedelta,
    ) -> bool:
        """Refresh the expiration of an active Socket.IO connection."""
        ...

    async def remove_socket(
        self,
        *,
        user_id: str,
        sid: str,
    ) -> None:
        """Remove an active Socket.IO connection."""
        ...

    async def get_socket_user(
        self,
        *,
        sid: str,
    ) -> str | None:
        """Return the user associated with an active SID."""
        ...
