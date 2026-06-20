"""Postgres-backed store for long-term memory with semantic search."""

import logging

from langgraph.store.postgres import AsyncPostgresStore

logger = logging.getLogger(__name__)

_store: AsyncPostgresStore | None = None
_conn = None


async def create_store(connection_string: str) -> AsyncPostgresStore:
    """Create and initialize the store with embedding support.

    Raises:
        ConnectionError: If Postgres is unreachable.
    """
    global _conn
    from app.embeddings.client import get_embedding_client

    try:
        embedding_client = get_embedding_client()
        index_config = {
            "dims": 768,
            "embed": embedding_client,
        }
        conn_ctx = AsyncPostgresStore.from_conn_string(
            conn_string=connection_string,
            index=index_config,
        )
        store = await conn_ctx.__aenter__()
        _conn = conn_ctx
        await store.setup()
        logger.info("Long-term store initialized")
        return store
    except Exception as e:
        raise ConnectionError(f"Store connection failed: {e}") from e


async def ensure_store() -> AsyncPostgresStore:
    """Get or create the singleton store."""
    global _store

    if _store is not None:
        return _store

    from app.config.settings import settings
    _store = await create_store(settings.supabase_db_url)
    return _store


async def shutdown_store():
    """Close the store connection on app shutdown."""
    global _store, _conn
    if _conn:
        try:
            await _conn.__aexit__(None, None, None)
        except Exception:
            pass
    _store = None
    _conn = None
