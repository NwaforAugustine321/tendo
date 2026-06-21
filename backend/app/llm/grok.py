"""Grok (xAI) LLM provider — connects to xAI's Grok models."""

from langchain_xai import ChatXAI

_client: ChatXAI | None = None


def get_client() -> ChatXAI:
    global _client
    if _client is None:
        from app.config.settings import settings
        _client = ChatXAI(
            model=settings.xai_model,
            xai_api_key=settings.xai_api_key,
        )
    return _client
