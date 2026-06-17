"""Anthropic LLM provider."""

from langchain_anthropic import ChatAnthropic

_client: ChatAnthropic | None = None


def get_client() -> ChatAnthropic:
    global _client
    if _client is None:
        from app.config.settings import settings
        _client = ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
        )
    return _client
