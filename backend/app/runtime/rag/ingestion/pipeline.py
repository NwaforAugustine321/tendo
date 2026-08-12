from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.runtime.rag.models import RAGDocument
from app.runtime.rag.store import RAGStore

from .loader import DocumentLoader
from .splitter import DocumentSplitter


@dataclass(slots=True)
class IngestionResult:
    """
    Result of one ingestion run.
    """

    documents: int = 0

    chunks: int = 0

    #
    # Chunked documents produced by the pipeline.
    #
    entries: list[RAGDocument] = field(
        default_factory=list,
    )


class DocumentIngestionPipeline:
    """
    Default document ingestion pipeline.

        Source
            │
            ▼
        Loader
            │
            ▼
        Documents
            │
            ▼
        Splitter
            │
            ▼
        Chunks
            │
            ▼
        Store (optional)
    """

    def __init__(
        self,
        *,
        loader: DocumentLoader,
        splitter: DocumentSplitter,
        store: RAGStore | None = None,
    ) -> None:

        self._loader = loader
        self._splitter = splitter
        self._store = store

    @property
    def loader(
        self,
    ) -> DocumentLoader:
        """
        Document loader.
        """

        return self._loader

    @property
    def splitter(
        self,
    ) -> DocumentSplitter:
        """
        Document splitter.
        """

        return self._splitter

    @property
    def store(
        self,
    ) -> RAGStore | None:
        """
        Optional target store.
        """

        return self._store

    async def ingest(
        self,
        *,
        source: str | Path | Any,
        content_type: str | None = None,
    ) -> IngestionResult:
        """
        Load, split and optionally index a document.

        If content_type is provided, it is used to
        select the loader directly (e.g. "text", "pdf",
        "image", "audio"). Otherwise the loader is
        determined from the source file extension.
        """

        documents = await self._loader.load(
            source=source,
            content_type=content_type,
        )

        document_count = len(
            documents,
        )

        if document_count == 0:
            return IngestionResult()

        chunks = await self._splitter.split(
            documents,
        )

        chunk_count = len(
            chunks,
        )

        if chunk_count == 0:
            return IngestionResult(
                documents=document_count,
            )

        if self._store is not None:

            await self._store.add(
                documents=chunks,
            )

        return IngestionResult(
            documents=document_count,
            chunks=chunk_count,
            entries=chunks,
        )
