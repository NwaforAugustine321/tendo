"""Gemini LLM provider."""

from langchain_google_genai import ChatGoogleGenerativeAI

_client: ChatGoogleGenerativeAI | None = None


def get_client() -> ChatGoogleGenerativeAI:
    global _client
    if _client is None:
        from app.config.settings import settings
        _client = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_voice_api_key,
        )
    return _client
