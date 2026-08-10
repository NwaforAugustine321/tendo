from __future__ import annotations
from app.embeddings.nvidia import get_client
from .provider import EmbeddingProvider
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from langchain_core.embeddings import Embeddings


class ENvidiaEmbedding(
    EmbeddingProvider,
):

    def __init__(
        self,
        target_dim: int = 768
    ) -> None:

        self._base = NVIDIAEmbeddings(
            model=settings.nvidia_embedding_model,
            api_key=settings.nvidia_api_key,
            truncate="END",
        )
        self._target_dim = target_dim

    @property
    def dimension(
        self,
    ) -> int:

        return 768

    async def embed(
        self,
        text: str,
    ) -> list[float]:

        return await self._aembed_query(
            text,
        )

    async def embed_documents(
        self,
        documents: list[str],
    ) -> list[list[float]]:

        return await self._aembed_documents(
            documents,
        )

    def _embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._base.embed_documents(texts)
        return [v[: self._target_dim] for v in vectors]

    def _embed_query(self, text: str, input_type: str = "query") -> list[float]:
        if input_type == "passage":
            vectors = self._base.embed_documents([text])
            return vectors[0][: self._target_dim] if vectors else [0.0] * self._target_dim
        vector = self._base.embed_query(text)
        return vector[: self._target_dim]

    async def _aembed_query(self, text: str, input_type: str = "query") -> list[float]:
        if input_type == "passage":
            vectors = await self._base.aembed_documents([text])
            return vectors[0][: self._target_dim] if vectors else [0.0] * self._target_dim
        vectors = await self._base.aembed_documents([text])
        return vectors[0][: self._target_dim] if vectors else [0.0] * self._target_dim

    async def _aembed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = await self._base.aembed_documents(texts)
        return [v[: self._target_dim] for v in vectors]
