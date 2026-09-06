"""Application settings."""

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str
    redis_url: str = ""

    # MongoDB
    mongodb_url: str = ""
    mongodb_user: str = ""
    mongodb_pass: str = ""
    mongodb_database: str

    minio_endpoint: str
    minio_public_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool

    # LLM
    llm_provider: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = ""
    gemini_model: str = ""
    ollama_model: str = ""
    ollama_base_url: str = ""

    webhook_internal_secret: str
    voice_agent_webhook_url: str
    webhook_default_timeout: int = 60.0

    # Msty (local OpenAI-compatible)
    msty_model: str = ""
    msty_base_url: str = ""
    msty_num_ctx: int = 4096

    # LMStudio (local OpenAI-compatible)
    lmstudio_model: str = ""
    lmstudio_base_url: str = ""

    # NVIDIA AI Endpoints
    nvidia_api_key: str = ""
    nvidia_embedding_model: str = "nvidia/llama-nemotron-embed-vl-1b-v2"
    nvidia_rerank_model: str = "nv-rerank-qa-mistral-4b:1"
    nvidia_model: str = ""

    # Storage
    bucket_name: str = ""
    vector_store_path: str = "./data/vector_store"

    # Voice
    google_voice_api_key: str = ""

    # LiveKit
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    # Dev
    spec_hot_reload: bool = True

    # Agent
    agent_name: str = ""

    # Business Event System Worker
    event_min_event_count: int
    event_min_char_count: int
    event_max_events_per_batch: int
    event_polling_interval_seconds: int
    event_max_batch_size: int

    # WhatsApp
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_api_version: str = ""
    whatsapp_app_id: str = ""
    whatsapp_test_token: str = ""

    # Business Event Scheduler
    event_max_concurrent_workers: int
    event_dispatcher_interval: int
    event_idle_eviction_cycles: int

    # Record Knowledge Engine
    record_knowledge_max_entries: int = 20
    record_knowledge_max_folder_entries: int = 200
    record_knowledge_max_summary_length: int = 2000
    record_knowledge_token_limit: int = 8000
    record_knowledge_max_retries: int = 3
    record_knowledge_llm_timeout: int = 30

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
