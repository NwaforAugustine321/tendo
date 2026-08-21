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
from ..interfaces import EventBus, EventTransport

logger = logging.getLogger(__name__)


class RedisTransport(EventTransport):
    """Redis implementation of the generic event transport."""

    _SOCKET_USER_PREFIX = "socket:user:"
    _SOCKET_SID_PREFIX = "socket:sid:"
    _SNAP_PREFIX = "snap:"

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

    # ==========================================================
    # Snap
    # ==========================================================

    def _snap_key(
        self,
        key: str,
    ) -> str:
        """
        Return the Redis key for a Snap record.

        Snap records are intentionally isolated under their own
        namespace so they do not interfere with other Redis data.
        """
        return (
            f"{self._SNAP_PREFIX}"
            f"{key}"
        )

    async def snap_set(
        self,
        *,
        key: str,
        value: dict[str, Any],
        ttl: timedelta,
    ) -> None:
        """
        Store a short-lived Snap record.

        The value is serialized as JSON and automatically expires
        after the supplied TTL.
        """
        if not key:
            raise ValueError(
                "key cannot be empty.",
            )

        if not isinstance(
            value,
            dict,
        ):
            raise TypeError(
                "value must be a dictionary.",
            )

        if ttl.total_seconds() <= 0:
            raise ValueError(
                "ttl must be greater than zero.",
            )

        payload = json.dumps(
            value,
            default=str,
        )

        await self._redis.set(
            self._snap_key(key),
            payload,
            ex=ttl,
        )

    async def snap_get(
        self,
        *,
        key: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve a Snap record.

        Returns None when the record does not exist or has expired.
        """
        if not key:
            return None

        payload = await self._redis.get(
            self._snap_key(key),
        )

        if payload is None:
            return None

        try:
            value = json.loads(
                payload,
            )
        except (
            json.JSONDecodeError,
            TypeError,
        ):
            return None

        if not isinstance(
            value,
            dict,
        ):
            return None

        return value

    async def snap_delete(
        self,
        *,
        key: str,
    ) -> bool:
        """
        Delete a Snap record.

        Returns True when a record was deleted.
        """
        if not key:
            return False

        deleted = await self._redis.delete(
            self._snap_key(key),
        )

        return bool(
            deleted,
        )

    async def snap_exists(
        self,
        *,
        key: str,
    ) -> bool:
        """Return whether a Snap record currently exists."""
        if not key:
            return False

        return bool(
            await self._redis.exists(
                self._snap_key(key),
            )
        )

    async def snap_expire(
        self,
        *,
        key: str,
        ttl: timedelta,
    ) -> bool:
        """
        Update the TTL of an existing Snap record.

        Returns True when the expiration was applied.
        """
        if not key:
            return False

        if ttl.total_seconds() <= 0:
            raise ValueError(
                "ttl must be greater than zero.",
            )

        return bool(
            await self._redis.expire(
                self._snap_key(key),
                ttl,
            )
        )

    async def snap_keys(
        self,
        *,
        pattern: str = "*",
    ) -> list[str]:
        """
        Return Snap keys matching a pattern.

        Returned keys do not include the internal Snap prefix.
        """
        keys: list[str] = []

        async for key in self._redis.scan_iter(
            match=self._snap_key(pattern),
        ):
            if isinstance(
                key,
                bytes,
            ):
                key = key.decode(
                    "utf-8",
                )

            if key.startswith(
                self._SNAP_PREFIX,
            ):
                key = key[
                    len(self._SNAP_PREFIX):
                ]

            keys.append(
                key,
            )

        return keys

    async def snap_count(
        self,
        *,
        pattern: str = "*",
    ) -> int:
        """Return the number of active Snap records matching a pattern."""
        count = 0

        async for _ in self._redis.scan_iter(
            match=self._snap_key(pattern),
        ):
            count += 1

        return count

    async def close(self) -> None:
        """Close the Redis connection."""
        await self._redis.aclose()


class RedisEventBus(EventBus):
    """
    Redis-backed application event bus.

    Serializes and deserializes ApplicationEvent instances
    while RedisTransport handles the underlying transport.
    """

    def __init__(
        self,
        transport: EventTransport,
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
    config: EventBusConfig,
) -> RedisTransport:

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
