"""Postgres-backed checkpointer for short-term memory with connection pooling."""

import logging

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

logger = logging.getLogger(__name__)

_checkpointer: AsyncPostgresSaver | None = None
_conn = None


async def create_checkpointer(connection_string: str) -> AsyncPostgresSaver:
    """Create and initialize the checkpointer with a pooled connection.

    Raises:
        ConnectionError: If Postgres is unreachable.
    """
    global _conn
    try:
        conn_ctx = AsyncPostgresSaver.from_conn_string(connection_string)
        checkpointer = await conn_ctx.__aenter__()
        _conn = conn_ctx
        await checkpointer.setup()
        logger.info("Checkpointer initialized")
        return checkpointer
    except Exception as e:
        raise ConnectionError(f"Checkpointer connection failed: {e}") from e


async def ensure_checkpointer() -> AsyncPostgresSaver:
    """Get or create the singleton checkpointer."""
    global _checkpointer, _conn

    if _checkpointer is not None:
        return _checkpointer

    from app.config.settings import settings
    _checkpointer = await create_checkpointer(settings.supabase_db_url)
    return _checkpointer


async def shutdown_checkpointer():
    """Close the checkpointer connection on app shutdown."""
    global _checkpointer, _conn
    if _conn:
        try:
            await _conn.__aexit__(None, None, None)
        except Exception:
            pass
    _checkpointer = None
    _conn = None
