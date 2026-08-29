from __future__ import annotations

from abc import ABC, abstractmethod

from .context import RAGContext
from .models import RAGDocument


class RAGStore(ABC):
    """
    Persistent storage backend for Retrieval-Augmented Generation (RAG).

    A RAGStore is responsible only for indexing and retrieving
    knowledge documents. It has no knowledge of agents,
    prompts, conversations, or RunContext.
    """

    @abstractmethod
    async def retrieve(
        self,
        *,
        query: str,
        limit: int = 10,
    ) -> RAGContext:
        """
        Retrieve documents relevant to the supplied query.
        """
        ...

    @abstractmethod
    async def index(
        self,
        *,
        documents: list[RAGDocument],
    ) -> None:
        """
        Index one or more knowledge documents.
        """
        ...

    @abstractmethod
    async def delete(
        self,
        *,
        document_id: str,
    ) -> None:
        """
        Delete a document by its unique identifier.
        """
        ...
