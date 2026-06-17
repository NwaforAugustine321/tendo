"""LLM client singleton."""

from langchain_anthropic import ChatAnthropic

_client: ChatAnthropic | None = None


def get_client() -> ChatAnthropic:
    global _client
    if _client is None:
        from app.config.settings import settings

        _client = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=settings.anthropic_api_key,
        )
    return _client
