"""Application settings — loaded from environment."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str
    mem0_api_key: str
    redis_url: str = "redis://localhost:6379"
    anthropic_api_key: str
    google_voice_api_key: str = ""
    google_voice_model: str = "gemini-3.1-flash-live-preview"
    spec_hot_reload: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
