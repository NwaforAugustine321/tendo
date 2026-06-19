"""Application settings."""

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str
    mem0_api_key: str = ""
    redis_url: str = ""

    # LLM
    llm_provider: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = ""
    gemini_model: str = ""

    # Embeddings
    embedding_provider: str = ""
    gemini_embedding_model: str = ""
    openai_embedding_model: str = ""
    openai_api_key: str = ""

    # Memory system
    supabase_db_url: str = ""  
    max_message_token_size: int = 1024  # Range: 128–131072

    # Storage
    bucket_name: str = "business-assets"

    # Voice
    voice_provider: str = "gemini"
    google_voice_api_key: str = ""
    google_voice_model: str = ""
    wake_phrase: str = ""
    silence_timeout_seconds: int = 120

    # Dev
    spec_hot_reload: bool = True

    # Agent
    agent_name: str = ""

    @field_validator("max_message_token_size")
    @classmethod
    def validate_token_size(cls, v: int) -> int:
        if v < 128 or v > 131072:
            raise ValueError(
                f"MAX_MESSAGE_TOKEN_SIZE must be between 128 and 131072, got {v}"
            )
        return v

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
