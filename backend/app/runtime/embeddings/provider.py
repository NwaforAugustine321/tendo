from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """
    Base embedding provider.
    """

    @property
    @abstractmethod
    def dimension(
        self,
    ) -> int:
        """
        Embedding vector dimension.
        """
        ...

    @abstractmethod
    async def embed(
        self,
        text: str,
    ) -> list[float]:
        """
        Embed a single string.
        """
        ...

    @abstractmethod
    async def embed_documents(
        self,
        documents: list[str],
    ) -> list[list[float]]:
        """
        Embed multiple strings.
        """
        ...
