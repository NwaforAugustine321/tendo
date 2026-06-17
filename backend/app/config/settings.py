"""Application settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str
    mem0_api_key: str
    redis_url: str = "redis://localhost:6379"

    # LLM
    llm_provider: str = "anthropic"  # "anthropic" or "gemini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    gemini_model: str = "gemini-2.0-flash"

    # Voice
    google_voice_api_key: str = ""
    google_voice_model: str = "gemini-2.0-flash-live-001"

    # Dev
    spec_hot_reload: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
