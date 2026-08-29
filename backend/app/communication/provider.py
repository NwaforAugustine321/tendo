from __future__ import annotations

from .config import EventBusConfig
from .interfaces import EventBus
from .transports.redis import (
    RedisEventBus,
    RedisTransport,
    create_redis_transport,
)


class EventBusProvider:
    """Creates and manages the application EventBus and Redis transport."""

    def __init__(
        self,
        config: EventBusConfig,
    ) -> None:
        self._config = config
        self._transport: RedisTransport | None = None
        self._event_bus: EventBus | None = None

    def get(self) -> EventBus:
        """Return the shared EventBus instance for this process."""

        if self._event_bus is None:
            self._transport = create_redis_transport(
                self._config,
            )

            self._event_bus = RedisEventBus(
                transport=self._transport,
                channel=self._config.channel,
            )

        return self._event_bus

    def get_transport(self) -> RedisTransport:
        """
        Return the shared Redis transport for this process.

        The EventBus must be initialized before accessing its
        underlying transport.
        """

        if self._transport is None:
            self.get()

        if self._transport is None:
            raise RuntimeError(
                "Redis transport was not initialized.",
            )

        return self._transport

    async def close(self) -> None:
        """Close the EventBus and release its Redis transport."""

        if self._event_bus is None:
            return

        await self._event_bus.close()

        self._event_bus = None
        self._transport = None
