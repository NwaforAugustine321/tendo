
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from langchain_core.embeddings import Embeddings


class ENVIDIAEmbeddings(Embeddings):

    def __init__(self, base: NVIDIAEmbeddings, target_dim: int = 768):
        self._base = base
        self._target_dim = target_dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._base.embed_documents(texts)
        return [v[: self._target_dim] for v in vectors]

    def embed_query(self, text: str, input_type: str = "query") -> list[float]:
        if input_type == "passage":
            vectors = self._base.embed_documents([text])
            return vectors[0][: self._target_dim] if vectors else [0.0] * self._target_dim
        vector = self._base.embed_query(text)
        return vector[: self._target_dim]

    async def aembed_query(self, text: str, input_type: str = "query") -> list[float]:
        if input_type == "passage":
            vectors = await self._base.aembed_documents([text])
            return vectors[0][: self._target_dim] if vectors else [0.0] * self._target_dim
        vectors = await self._base.aembed_documents([text])
        return vectors[0][: self._target_dim] if vectors else [0.0] * self._target_dim

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = await self._base.aembed_documents(texts)
        return [v[: self._target_dim] for v in vectors]


_client: ENVIDIAEmbeddings | None = None


def get_client() -> ENVIDIAEmbeddings:
    global _client
    if _client is None:
        from app.config.settings import settings
        base = NVIDIAEmbeddings(
            model=settings.nvidia_embedding_model,
            api_key=settings.nvidia_api_key,
            truncate="END",
        )
        _client = ENVIDIAEmbeddings(base, target_dim=768)
    return _client
