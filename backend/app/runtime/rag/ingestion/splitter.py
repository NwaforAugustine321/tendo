from __future__ import annotations

from abc import ABC, abstractmethod

from app.runtime.rag.models import RAGDocument


class DocumentSplitter(ABC):
    """
    Splits documents into retrieval-sized chunks.

    Implementations may use recursive character splitting,
    token splitting, semantic chunking, Markdown-aware
    splitting, or any other strategy.
    """

    @abstractmethod
    async def split(
        self,
        documents: list[RAGDocument],
    ) -> list[RAGDocument]:
        """
        Split documents into retrieval-sized chunks.
        """
        ...
