from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.runtime.rag.models import RAGDocument


class DocumentLoader(ABC):
    """
    Loads external content and converts it into RAG documents.

    Implementations may support files, directories,
    URLs, cloud storage, databases, APIs, etc.
    """

    @abstractmethod
    async def load(
        self,
        *,
        source: str | Path | Any,
        content_type: str | None = None,
    ) -> list[RAGDocument]:
        """
        Load one source into RAG documents.

        If content_type is provided, it can be used
        to determine how to process the source without
        relying on file extension detection.
        """
        ...
