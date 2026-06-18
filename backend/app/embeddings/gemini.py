"""Gemini embedding provider using models/gemini-embedding-001."""

from langchain_google_genai import GoogleGenerativeAIEmbeddings

_client: GoogleGenerativeAIEmbeddings | None = None


def get_client() -> GoogleGenerativeAIEmbeddings:
    global _client
    if _client is None:
        from app.config.settings import settings
        _client = GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            google_api_key=settings.google_voice_api_key,
            output_dimensionality=768
        )
    return _client
