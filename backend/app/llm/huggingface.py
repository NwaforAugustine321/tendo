"""HuggingFace Inference provider — uses HF Inference API with configurable provider."""

from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

_client: ChatHuggingFace | None = None


def get_client() -> ChatHuggingFace:
    global _client
    if _client is None:
        from app.config.settings import settings
        llm = HuggingFaceEndpoint(
            repo_id=settings.hf_model,
            huggingfacehub_api_token=settings.hf_token,
            task="text-generation",
        )
        _client = ChatHuggingFace(llm=llm)
    return _client
