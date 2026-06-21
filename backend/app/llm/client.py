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
    elif settings.llm_provider == "ollama":
        from app.llm.ollama import get_client as get_ollama
        _client = get_ollama()
    elif settings.llm_provider == "huggingface":
        from app.llm.huggingface import get_client as get_hf
        _client = get_hf()
    elif settings.llm_provider == "grok":
        from app.llm.grok import get_client as get_grok
        _client = get_grok()
    elif settings.llm_provider == "groq":
        from app.llm.groq import get_client as get_groq
        _client = get_groq()
    else:
        from app.llm.anthropic import get_client as get_anthropic
        _client = get_anthropic()

    return _client
