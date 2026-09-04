"""Application settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str

    mongodb_url: str = ""
    mongodb_user: str = ""
    mongodb_pass: str = ""
    mongodb_database: str = "tendo"

    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    nvidia_api_key: str
    webhook_internal_secret: str
    main_server_webhook_url: str
    webhook_default_timeout: int = 60.0

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_nested_delimiter": "__",
        "extra": "ignore",
    }


settings = Settings()
