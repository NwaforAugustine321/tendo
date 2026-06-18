"""Supabase-backed store for long-term memory with semantic search."""

import logging

from langgraph.store.postgres import AsyncPostgresStore

logger = logging.getLogger(__name__)

_store: AsyncPostgresStore | None = None
_conn = None  # Hold reference to the async context manager


async def create_store(connection_string: str) -> AsyncPostgresStore:
    """Create and initialize the Supabase-backed store.

    Uses the embedding client from app/embeddings/ for semantic search.

    Args:
        connection_string: PostgreSQL connection string for Supabase.

    Returns:
        Initialized AsyncPostgresStore ready for graph compilation.

    Raises:
        ConnectionError: If Supabase is unreachable within 30s.
    """
    global _conn
    from app.embeddings.client import get_embedding_client

    try:
        embedding_client = get_embedding_client()

        # Configure the index with embedding function for semantic search
        index_config = {
            "dims": 768,  # text-embedding-004 outputs 768 dims
            "embed": embedding_client,
        }

        conn_ctx = AsyncPostgresStore.from_conn_string(
            conn_string=connection_string,
            index=index_config,
        )
        store = await conn_ctx.__aenter__()
        _conn = conn_ctx  # Keep reference so connection isn't garbage collected
        await store.setup()
        logger.info("Supabase store initialized successfully")
        return store
    except Exception as e:
        raise ConnectionError(
            f"Failed to connect to Supabase for store: {e}"
        ) from e


async def ensure_store() -> AsyncPostgresStore:
    """Singleton accessor that initializes on first call."""
    global _store
    if _store is not None:
        return _store

    from app.config.settings import settings

    _store = await create_store(settings.supabase_db_url)
    return _store
