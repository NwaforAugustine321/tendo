from __future__ import annotations

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

_client: AsyncMongoClient | None = None


def get_client() -> AsyncDatabase:
    from app.config.settings import settings

    global _client

    if _client is None:
        _client = AsyncMongoClient(
            settings.mongodb_url,
        )

    return _client[settings.mongodb_database]
