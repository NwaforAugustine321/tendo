"""Supabase-backed checkpointer for short-term memory."""

import logging

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

logger = logging.getLogger(__name__)

_checkpointer: AsyncPostgresSaver | None = None
_conn = None  # Hold reference to the async context manager


async def create_checkpointer(connection_string: str) -> AsyncPostgresSaver:
    """Create and initialize the Supabase-backed checkpointer.

    Args:
        connection_string: PostgreSQL connection string for Supabase.

    Returns:
        Initialized AsyncPostgresSaver ready for graph compilation.

    Raises:
        ConnectionError: If Supabase is unreachable.
    """
    global _conn
    try:
        conn_ctx = AsyncPostgresSaver.from_conn_string(connection_string)
        checkpointer = await conn_ctx.__aenter__()
        _conn = conn_ctx  # Keep reference so connection isn't garbage collected
        await checkpointer.setup()
        logger.info("Supabase checkpointer initialized successfully")
        return checkpointer
    except Exception as e:
        raise ConnectionError(
            f"Failed to connect to Supabase for checkpointer: {e}"
        ) from e


async def ensure_checkpointer() -> AsyncPostgresSaver:
    """Singleton accessor that initializes on first call."""
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    from app.config.settings import settings

    _checkpointer = await create_checkpointer(settings.supabase_db_url)
    return _checkpointer
