from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from ..config import EventBusConfig
from ..events import ApplicationEvent
from ..interfaces import EventBus, Transport

logger = logging.getLogger(__name__)


class RedisTransport(Transport):
    """Redis implementation of the generic event transport."""

    _SOCKET_USER_PREFIX = "socket:user:"
    _SOCKET_SID_PREFIX = "socket:sid:"

    def __init__(
        self,
        redis: Redis,
    ) -> None:
        self._redis = redis

    async def publish(
        self,
        channel: str,
        payload: str,
    ) -> None:
        """Publish a payload to a Redis channel."""
        try:
            await self._redis.publish(
                channel,
                payload,
            )
        except (
            RedisConnectionError,
            ConnectionResetError,
            OSError,
        ):
            # One retry after reconnect attempt.
            try:
                await self._redis.publish(
                    channel,
                    payload,
                )
            except (
                RedisConnectionError,
                ConnectionResetError,
                OSError,
            ) as exc:
                raise RedisConnectionError(
                    f"Redis publish failed after retry: {exc}"
                ) from exc

    def subscribe(
        self,
        channel: str,
    ) -> AsyncIterator[str]:
        """Subscribe to a Redis channel."""
        return self._subscribe(
            channel,
        )

    async def _subscribe(
        self,
        channel: str,
    ) -> AsyncIterator[str]:
        backoff = 1.0
        max_backoff = 30.0

        while True:
            pubsub = self._redis.pubsub()

            try:
                # Force a fresh connection check before subscribing
                await self._redis.ping()

                await pubsub.subscribe(
                    channel,
                )

                backoff = 1.0

                async for message in pubsub.listen():

                    if message.get("type") != "message":
                        continue

                    payload = message.get(
                        "data",
                    )

                    if isinstance(
                        payload,
                        bytes,
                    ):
                        payload = payload.decode(
                            "utf-8",
                        )

                    if not isinstance(
                        payload,
                        str,
                    ):
                        continue

                    yield payload

            except (
                RedisConnectionError,
                ConnectionResetError,
                OSError,
            ):
                logger.warning(
                    "Redis pub/sub connection lost, "
                    "reconnecting in %.1fs…",
                    backoff,
                )

                await asyncio.sleep(
                    backoff,
                )

                backoff = min(
                    backoff * 2,
                    max_backoff,
                )

            except asyncio.CancelledError:
                raise

            finally:
                try:
                    await pubsub.unsubscribe(
                        channel,
                    )
                except Exception:
                    pass

                try:
                    await pubsub.aclose()
                except Exception:
                    pass

    # ==========================================================
    # Key/value storage
    #
    # Values are stored as JSON so callers can persist and read
    # back plain dictionaries.
    # ==========================================================

    async def set(
        self,
        *,
        key: str,
        value: dict[str, Any],
        ttl: timedelta | None = None,
    ) -> None:
        """
        Store a JSON-serializable value, optionally with a TTL.
        """

        if not key:
            raise ValueError(
                "key cannot be empty.",
            )

        payload = json.dumps(
            value,
            default=str,
        )

        if ttl is not None:
            await self._redis.set(
                key,
                payload,
                ex=ttl,
            )
            return

        await self._redis.set(
            key,
            payload,
        )

    async def get(
        self,
        *,
        key: str,
    ) -> dict[str, Any] | None:
        """
        Read a stored value.

        Returns None when the key is absent or does not hold a
        JSON object.
        """

        if not key:
            return None

        raw = await self._redis.get(
            key,
        )

        if raw is None:
            return None

        if isinstance(
            raw,
            bytes,
        ):
            raw = raw.decode(
                "utf-8",
            )

        try:
            decoded = json.loads(
                raw,
            )
        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            return None

        if not isinstance(
            decoded,
            dict,
        ):
            return None

        return decoded

    async def delete(
        self,
        *,
        key: str,
    ) -> None:
        """
        Remove a key. Missing keys are ignored.
        """

        if not key:
            return

        await self._redis.delete(
            key,
        )

    async def expire(
        self,
        *,
        key: str,
        ttl: timedelta,
    ) -> bool:
        """
        Reset a key's TTL.

        Returns False when the key does not exist.
        """

        if not key:
            return False

        return bool(
            await self._redis.expire(
                key,
                ttl,
            )
        )

    async def keys(
        self,
        *,
        pattern: str,
    ) -> list[str]:
        """
        Return keys matching a pattern.

        SCAN is used instead of KEYS because KEYS is O(N) and
        blocks the Redis server for the duration of the sweep.
        """

        if not pattern:
            return []

        found: list[str] = []

        async for key in self._redis.scan_iter(
            match=pattern,
            count=100,
        ):

            if isinstance(
                key,
                bytes,
            ):
                key = key.decode(
                    "utf-8",
                )

            found.append(
                key,
            )

        return found

    # ==========================================================
    # Socket helpers
    # ==========================================================

    def _user_socket_key(
        self,
        user_id: str,
    ) -> str:
        """Return the Redis key containing a user's active SIDs."""
        return (
            f"{self._SOCKET_USER_PREFIX}"
            f"{user_id}"
        )

    def _socket_key(
        self,
        sid: str,
    ) -> str:
        """Return the Redis key for an individual Socket.IO SID."""
        return (
            f"{self._SOCKET_SID_PREFIX}"
            f"{sid}"
        )

    async def add_socket(
        self,
        *,
        user_id: str,
        sid: str,
        ttl: timedelta,
    ) -> None:
        """
        Register an active Socket.IO connection.

        Redis stores:

            socket:user:{user_id} -> active SID set
            socket:sid:{sid}       -> user ID with expiration
        """
        if not user_id or not sid:
            return

        user_key = self._user_socket_key(
            user_id,
        )

        sid_key = self._socket_key(
            sid,
        )

        async with self._redis.pipeline(
            transaction=True,
        ) as pipe:
            await (
                pipe.sadd(
                    user_key,
                    sid,
                )
                .set(
                    sid_key,
                    user_id,
                    ex=ttl,
                )
                .execute()
            )

    async def get_sockets(
        self,
        *,
        user_id: str,
    ) -> list[str]:
        """
        Return currently active Socket.IO SIDs for a user.

        Redis automatically expires individual SID keys.
        The user SID set is cleaned lazily when expired SIDs
        are encountered.
        """
        if not user_id:
            return []

        user_key = self._user_socket_key(
            user_id,
        )

        sids = await self._redis.smembers(
            user_key,
        )

        if not sids:
            return []

        active_sids: list[str] = []

        for sid in sids:

            sid_key = self._socket_key(
                sid,
            )

            if await self._redis.exists(
                sid_key,
            ):
                active_sids.append(
                    sid,
                )
            else:
                await self._redis.srem(
                    user_key,
                    sid,
                )

        if not active_sids:
            await self._redis.delete(
                user_key,
            )

        return active_sids

    async def refresh_socket(
        self,
        *,
        sid: str,
        ttl: timedelta,
    ) -> bool:
        """
        Refresh the expiration of an active Socket.IO connection.

        Returns True when the SID key exists and its expiration
        was successfully refreshed.
        """
        if not sid:
            return False

        sid_key = self._socket_key(
            sid,
        )

        return bool(
            await self._redis.expire(
                sid_key,
                ttl,
            )
        )

    async def remove_socket(
        self,
        *,
        user_id: str,
        sid: str,
    ) -> None:
        """Remove a Socket.IO connection from Redis."""
        if not user_id or not sid:
            return

        user_key = self._user_socket_key(
            user_id,
        )

        sid_key = self._socket_key(
            sid,
        )

        async with self._redis.pipeline(
            transaction=True,
        ) as pipe:
            await (
                pipe.srem(
                    user_key,
                    sid,
                )
                .delete(
                    sid_key,
                )
                .execute()
            )

        if await self._redis.scard(
            user_key,
        ) == 0:
            await self._redis.delete(
                user_key,
            )

    async def get_socket_user(
        self,
        *,
        sid: str,
    ) -> str | None:
        """
        Return the user ID associated with an active SID.

        Returns None when the SID has expired or does not exist.
        """
        if not sid:
            return None

        user_id = await self._redis.get(
            self._socket_key(sid),
        )

        if isinstance(
            user_id,
            bytes,
        ):
            return user_id.decode(
                "utf-8",
            )

        return user_id


class RedisEventBus(EventBus):
    """
    Redis-backed application event bus.

    Serializes and deserializes ApplicationEvent instances
    while RedisTransport handles the underlying transport.
    """

    def __init__(
        self,
        transport: Transport,
        *,
        channel: str = "application.events",
    ) -> None:
        self._transport = transport
        self._channel = channel

    async def publish(
        self,
        event: ApplicationEvent,
    ) -> None:

        payload = json.dumps(
            event.to_dict(),
            default=str,
        )

        try:
            await self._transport.publish(
                self._channel,
                payload,
            )
        except (
            RedisConnectionError,
            ConnectionResetError,
            OSError,
        ) as exc:
            logger.warning(
                "EventBus publish failed (Redis unavailable): %s",
                exc,
            )

    def subscribe(
        self,
        event: str | None = None,
    ) -> AsyncIterator[ApplicationEvent]:

        return self._subscribe(
            event,
        )

    async def _subscribe(
        self,
        event: str | None,
    ) -> AsyncIterator[ApplicationEvent]:

        async for payload in self._transport.subscribe(
            self._channel,
        ):

            try:
                application_event = (
                    ApplicationEvent.from_dict(
                        json.loads(
                            payload,
                        ),
                    )
                )

            except (
                json.JSONDecodeError,
                TypeError,
                ValueError,
            ):
                continue

            if (
                event is not None
                and application_event.event != event
            ):
                continue

            yield application_event

    async def close(self) -> None:
        await self._transport.close()


def create_redis_transport(
    config: EventBusConfig | None = None,
    url: str | None = None
) -> RedisTransport:

    if url:
        url = url

    if config:
        url = config.options.get(
            "url",
        )

    if not url:
        raise ValueError(
            "Redis transport requires "
            "'url' in EventBusConfig.options."
        )

    redis = Redis.from_url(
        url,
        decode_responses=True,
    )

    return RedisTransport(
        redis,
    )
