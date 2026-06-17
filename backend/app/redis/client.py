"""Redis client singleton."""

import redis

_client: redis.Redis | None = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        from app.config.settings import settings

        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client
