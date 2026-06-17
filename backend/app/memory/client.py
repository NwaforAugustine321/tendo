"""Memory client singleton — only place that imports mem0."""

from mem0 import MemoryClient

_client: MemoryClient | None = None


def get_client() -> MemoryClient:
    global _client
    if _client is None:
        from app.config.settings import settings

        _client = MemoryClient(api_key=settings.mem0_api_key)
    return _client
