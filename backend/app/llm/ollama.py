"""Ollama LLM provider — connects to local Ollama instance."""

from langchain_ollama import ChatOllama

_client: ChatOllama | None = None


def get_client() -> ChatOllama:
    global _client
    if _client is None:
        from app.config.settings import settings
        _client = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            # num_ctx=8129,
            num_ctx=4096
        )
    return _client
