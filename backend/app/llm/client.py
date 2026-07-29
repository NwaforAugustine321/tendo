"""LLM client — routes to configured provider and creates instances."""

_client = None


def get_client(callbacks=None):
    """Get the LLM client. If callbacks provided, returns a fresh instance with callbacks."""
    global _client

    if callbacks:
        return _create_client(callbacks=callbacks)

    if _client is not None:
        return _client

    _client = _create_client()
    return _client


def _create_client(callbacks=None):
    """Create an LLM client instance for the configured provider."""
    from app.config.settings import settings

    cb = callbacks or []

    if settings.llm_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_voice_api_key,
            streaming=True,
            callbacks=cb,
        )

    elif settings.llm_provider == "ollama":
        from langchain_openai import ChatOpenAI
       
       
        return ChatOpenAI(
            model=settings.ollama_model,
            base_url=f"{settings.ollama_base_url}/v1",
            # base_url=f"{settings.ollama_base_url}/api/v1",
            streaming=True,
            api_key='ollama',
            # api_key='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',
            callbacks=cb,
            model_kwargs={
               "extra_body": {
                "max_soft_tokens": 1120,
                "temperature": 1.0,
                "top_p":0.95,
             }
             }
        )

    elif settings.llm_provider == "huggingface":
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
        llm = HuggingFaceEndpoint(
            repo_id=settings.hf_model,
            huggingfacehub_api_token=settings.hf_token,
            task="text-generation",
        )
        return ChatHuggingFace(llm=llm, callbacks=cb)

    elif settings.llm_provider == "grok":
        from langchain_xai import ChatXAI
        return ChatXAI(
            model=settings.xai_model,
            xai_api_key=settings.xai_api_key,
            streaming=True,
            callbacks=cb,
        )

    elif settings.llm_provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            streaming=True,
            callbacks=cb,
        )

    elif settings.llm_provider == "msty":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.msty_model,
            base_url=settings.msty_base_url,
            api_key="msty",
            streaming=True,
            callbacks=cb,
            extra_body={"options": {"num_ctx": settings.msty_num_ctx}},
        )

    elif settings.llm_provider == "lmstudio":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.lmstudio_model,
            base_url=settings.lmstudio_base_url,
            api_key="lmstudio",
            streaming=True,
            callbacks=cb,
        )

    elif settings.llm_provider == "nvidia":
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        return ChatNVIDIA(
            model=settings.nvidia_model,
            api_key=settings.nvidia_api_key,
            callbacks=cb,
            timeout=None,
            temperature=0.6,
            top_p=0.95,
            
        )
        

    else:
        # Default: Anthropic
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            streaming=True,
            callbacks=cb,
        )
