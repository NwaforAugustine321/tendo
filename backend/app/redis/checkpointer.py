"""LangGraph Redis checkpointer setup."""

from langgraph.checkpoint.redis import RedisSaver

from app.redis.client import get_client

_checkpointer: RedisSaver | None = None


def get_checkpointer() -> RedisSaver:
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = RedisSaver(get_client())
    return _checkpointer
