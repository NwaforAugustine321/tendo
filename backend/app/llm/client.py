"""LLM client — routes to configured provider (anthropic or gemini)."""


def get_client():
    from app.config.settings import settings

    if settings.llm_provider == "gemini":
        from app.llm.gemini import get_client as get_gemini
        return get_gemini()

    from app.llm.anthropic import get_client as get_anthropic
    return get_anthropic()
