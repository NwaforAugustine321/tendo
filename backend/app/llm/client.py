from langchain_openai import ChatOpenAI
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_xai import ChatXAI
from langchain_groq import ChatGroq
from app.config.settings import settings

_client = None


def get_client(config: dict | None = {}, callbacks=None):
    """Get the LLM client. If callbacks provided, returns a fresh instance with callbacks."""
    global _client

    if callbacks:
        return _create_client(config=config, callbacks=callbacks)

    if _client is not None:
        return _client

    _client = _create_client()
    return _client


def get_guard_client():
    return ChatNVIDIA(
        # model="meta/llama-3.1-8b-instruct",
        # model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
        # model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        model="nvidia/llama-3.1-nemotron-safety-guard-8b-v3",
        api_key=settings.nvidia_api_key,
        timeout=None,
        temperature=0.0,
        max_tokens=32,
        top_p=0.05
    ).with_thinking_mode(enabled=True)


def _create_client(config: dict | None = {}, callbacks=None, provider=None):

    cb = callbacks or []
    _provider = provider if provider else settings.llm_provider
    max_token = config.get("max_token", 4096)

    if _provider == "gemini":

        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_voice_api_key,
            streaming=True,
            callbacks=cb,
            timeout=None,
            max_tokens=max_token
        )

    elif _provider == "ollama":

        return ChatOpenAI(
            model=settings.ollama_model,
            base_url=f"{settings.ollama_base_url}/v1",
            streaming=True,
            api_key='ollama',
            callbacks=cb,
            timeout=None,
            max_tokens=max_token,
            temperature=0.6,
            model_kwargs={
                "extra_body": {
                    "max_soft_tokens": 1120,
                    # "temperature": 0.6,
                    "top_p": 0.95,
                }
            }
        )

    elif _provider == "huggingface":

        llm = HuggingFaceEndpoint(
            repo_id=settings.hf_model,
            huggingfacehub_api_token=settings.hf_token,
            task="text-generation",
        )
        return ChatHuggingFace(llm=llm, callbacks=cb)

    elif _provider == "grok":

        return ChatXAI(
            model=settings.xai_model,
            xai_api_key=settings.xai_api_key,
            streaming=True,
            callbacks=cb,
            timeout=None,
        )

    elif _provider == "groq":

        return ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            streaming=True,
            callbacks=cb,
            timeout=None,
        )

    elif _provider == "msty":

        return ChatOpenAI(
            model=settings.msty_model,
            base_url=settings.msty_base_url,
            api_key="msty",
            streaming=True,
            callbacks=cb,
            timeout=None,
            extra_body={"options": {"num_ctx": settings.msty_num_ctx}},
        )

    elif _provider == "lmstudio":

        return ChatOpenAI(
            model=settings.lmstudio_model,
            base_url=settings.lmstudio_base_url,
            api_key="lmstudio",
            streaming=True,
            callbacks=cb,
            timeout=None,
        )

    elif _provider == "nvidia":

        return ChatNVIDIA(
            # model=settings.nvidia_model,
            # model="nvidia/nemotron-3-super-120b-a12b",
            model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            api_key=settings.nvidia_api_key,
            callbacks=cb,
            timeout=None,
            temperature=0.6,
            top_p=0.95,
            max_tokens=max_token,
            reasoning_budget=150,
            chat_template_kwargs={
                "enable_thinking": True,
                # "low_effort":True,
                # "reasoning_budget":150
            }


        )

    else:
        # Default: Anthropic
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            streaming=True,
            callbacks=cb,
            timeout=None,
        )
