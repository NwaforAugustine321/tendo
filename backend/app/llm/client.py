"""LLM client — routes to configured provider."""

_client = None


def get_client():
    global _client
    if _client is not None:
        return _client

    from app.config.settings import settings

    if settings.llm_provider == "gemini":
        from app.llm.gemini import get_client as get_gemini
        _client = get_gemini()
    else:
        from app.llm.anthropic import get_client as get_anthropic
        _client = get_anthropic()

    return _client
