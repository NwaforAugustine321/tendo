"""Msty LLM provider — connects to local Msty instance via OpenAI-compatible API."""

from langchain_openai import ChatOpenAI

_client: ChatOpenAI | None = None


def get_client() -> ChatOpenAI:
    global _client
    if _client is None:
        from app.config.settings import settings
        _client = ChatOpenAI(
            model=settings.msty_model,
            base_url=settings.msty_base_url,
            api_key="msty",
            extra_body={"options": {"num_ctx": settings.msty_num_ctx}},
        )
    return _client
