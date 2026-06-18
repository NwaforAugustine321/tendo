"""OpenAI embedding provider using text-embedding-3-small."""

from langchain_openai import OpenAIEmbeddings

_client: OpenAIEmbeddings | None = None


def get_client() -> OpenAIEmbeddings:
    global _client
    if _client is None:
        from app.config.settings import settings
        _client = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        )
    return _client
