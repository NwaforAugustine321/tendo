"""Supabase-backed checkpointer for short-term memory."""

import logging

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

logger = logging.getLogger(__name__)

_checkpointer: AsyncPostgresSaver | None = None
_conn = None  # Hold reference to the async context manager
_connection_string: str | None = None


async def create_checkpointer(connection_string: str) -> AsyncPostgresSaver:
    """Create and initialize the Supabase-backed checkpointer.

    Args:
        connection_string: PostgreSQL connection string for Supabase.

    Returns:
        Initialized AsyncPostgresSaver ready for graph compilation.

    Raises:
        ConnectionError: If Supabase is unreachable.
    """
    global _conn, _connection_string
    _connection_string = connection_string
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
    """Singleton accessor that initializes on first call. Reconnects if connection dropped."""
    global _checkpointer, _conn

    if _checkpointer is not None:
        # Test if connection is still alive
        try:
            # Quick check — if the internal connection is closed, reconnect
            if _conn and hasattr(_conn, 'gen') and _conn.gen.ag_frame is None:
                raise Exception("connection closed")
            return _checkpointer
        except Exception:
            logger.warning("Checkpointer connection lost, reconnecting...")
            _checkpointer = None
            _conn = None

    from app.config.settings import settings

    conn_str = _connection_string or settings.supabase_db_url
    _checkpointer = await create_checkpointer(conn_str)
    return _checkpointer
