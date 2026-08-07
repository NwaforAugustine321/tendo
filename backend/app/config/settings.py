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
    ollama_model: str = ""
    ollama_base_url: str = ""

    # HuggingFace Inference
    hf_token: str = ""
    hf_model: str = ""
    hf_provider: str = ""

    # Grok (xAI)
    xai_api_key: str = ""
    xai_model: str = ""

    # Groq (fast inference)
    groq_api_key: str = ""
    groq_model: str = ""

    # Msty (local OpenAI-compatible)
    msty_model: str = ""
    msty_base_url: str = ""
    msty_num_ctx: int = 4096

    # LMStudio (local OpenAI-compatible)
    lmstudio_model: str = ""
    lmstudio_base_url: str = ""

    # NVIDIA AI Endpoints
    nvidia_api_key: str = ""
    nvidia_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    nvidia_embedding_model: str = "nvidia/llama-nemotron-embed-vl-1b-v2"
    nvidia_temperature: float = 0.6
    nvidia_top_p: float = 0.95
    nvidia_max_tokens: int = 65536
    nvidia_reasoning_budget: int = 16384
    nvidia_rerank_model: str = "nv-rerank-qa-mistral-4b:1"
    stt_function_id: str = "71203149-d3b7-4460-8231-1be2543a1fca"
    tts_function_id: str = "77a3a03e-43de-4988-9368-88792561aabc"
    tts_voice: str = "English-US-RadTTS.Male-1"
   

    # Tool calling mode: whether LLM supports native function calling
    # Set to false for local models (lmstudio, ollama, msty) that use ReAct text instead
    native_tool_calling: bool = True

    # Embeddings
    embedding_provider: str = ""
    gemini_embedding_model: str = ""
    openai_embedding_model: str = ""
    openai_api_key: str = ""

    # Memory system
    supabase_db_url: str = ""
    max_message_token_size: int = 1024  # Range: 128–131072

    # Storage
    bucket_name: str = ""
    supabase_storage_bucket: str = ""
    vector_store_path: str = "./data/vector_store"

    # Voice
    voice_provider: str = ""
    google_voice_api_key: str = ""
    google_voice_model: str = ""
    cartesia_api_key: str = ""
    cartesia_voice_id: str = ""
    cartesia_stt_model: str = "ink-2"
    cartesia_tts_model: str = "sonic-2"
    cartesia_language: str = "en"  # Cartesia multilingual: en, es, fr, de, pt, ja, zh, hi, etc.
    wake_phrase: str = ""
    silence_timeout_seconds: int = 120

    # LiveKit
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    # Feature flags
    use_planner_path: bool = False

    # Dev
    spec_hot_reload: bool = True

    # Agent
    agent_name: str = ""

    # Intelligence Agent
    intelligence_llm_provider: str = "msty"
    intelligence_llm_model: str = ""
    intelligence_max_iterations: int = 5
    intelligence_embedding_batch_size: int = 10

    # Graph Database
    graph_db_uri: str = "bolt://localhost:7687"
    graph_db_user: str = "neo4j"
    graph_db_password: str = ""
    graph_db_name: str = "neo4j"

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
    whatsapp_config_id: str = ""
    whatsapp_redirect_uri: str = ""
    whatsapp_test_token:str = ""

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
