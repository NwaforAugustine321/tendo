"""LLM client — routes to configured provider."""

_client = None


def get_client():
    global _client
    if _client is not None:
        return _client

    from app.config.settings import settings

    if settings.llm_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        _client = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_voice_api_key,
        )
    else:
        from langchain_anthropic import ChatAnthropic
        _client = ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
        )

    return _client
