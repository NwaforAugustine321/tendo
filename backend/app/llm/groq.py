"""Groq LLM provider — fast inference for open models."""

from langchain_groq import ChatGroq

_client: ChatGroq | None = None


def get_client() -> ChatGroq:
    global _client
    if _client is None:
        from app.config.settings import settings
        _client = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
        )
    return _client
