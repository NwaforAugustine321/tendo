from __future__ import annotations

from pathlib import Path
from typing import Any

from app.runtime.agents.run_context import RunContext

from .context import RAGContext
from .ingestion.pipeline import (
    DocumentIngestionPipeline,
    IngestionResult,
)
from .models import RAGDocument
from .retrieval import RetrievalEngine
from .store import RAGStore
from app.runtime.context_manager.optimizers.optimizer import (
    ContextOptimizer as Optimizer,
    OptimizationResult,
)
from app.runtime.context_manager.optimizers.default_optimizer import (
    DefaultConversationOptimizer,
)


class RAGProvider:
    """
    Coordinates Retrieval-Augmented Generation (RAG).

    Responsibilities
    ----------------
    - Build retrieval queries.
    - Retrieve relevant knowledge.
    - Ingest new documents.
    - Add documents directly.
    - Delete documents.
    """

    def __init__(
        self,
        *,
        store: RAGStore,
        retrieval: RetrievalEngine,
        ingestion: DocumentIngestionPipeline | None = None,
        optimizer: Optimizer | None = None,
    ) -> None:

        self._store = store
        self._retrieval = retrieval
        self._ingestion = ingestion

        self._optimizer = (
            optimizer
            or DefaultConversationOptimizer(
                provider=self,
            )
        )

    @property
    def store(
        self,
    ) -> RAGStore:
        """
        Underlying document store.
        """

        return self._store

    @property
    def retrieval(
        self,
    ) -> RetrievalEngine:
        """
        Retrieval engine.
        """

        return self._retrieval

    @property
    def ingestion(
        self,
    ) -> DocumentIngestionPipeline | None:
        """
        Optional document ingestion pipeline.
        """

        return self._ingestion

    async def optimize(
        self,
        *,
        conversation: ConversationContext,
        current_tokens: int,
        target_tokens: int,
    ) -> OptimizationResult:

        return await self._optimizer.optimize(
            conversation=conversation,
            current_tokens=current_tokens,
            target_tokens=target_tokens,
        )

    async def retrieve(
        self,
        ctx: RunContext,
    ) -> RAGContext:
        """
        Retrieve documents relevant to the current run.
        """

        query = await self._retrieval.build_query(
            ctx,
        )

        if not query.strip():
            return RAGContext()

        return await self._store.retrieve(
            query=query,
        )

    async def ingest(
        self,
        *,
        source: str | Path | Any,
    ) -> IngestionResult:
        """
        Load, split and index a document.
        """

        if self._ingestion is None:

            raise RuntimeError(
                "RAG ingestion pipeline is not configured."
            )

        return await self._ingestion.ingest(
            source=source,
        )

    async def add(
        self,
        *,
        documents: list[RAGDocument],
    ) -> None:
        """
        Add documents directly to the knowledge store.
        """

        await self._store.add(
            documents=documents,
        )

    async def delete(
        self,
        *,
        document_id: str,
    ) -> None:
        """
        Delete a document from the knowledge store.
        """

        await self._store.delete(
            document_id=document_id,
        )
