"""Embedding client — routes to configured provider."""

_client = None


def get_embedding_client():
    global _client
    if _client is not None:
        return _client

    from app.config.settings import settings

    if settings.embedding_provider == "gemini":
        from app.embeddings.gemini import get_client as get_gemini
        _client = get_gemini()
    else:
        from app.embeddings.openai import get_client as get_openai
        _client = get_openai()

    return _client
