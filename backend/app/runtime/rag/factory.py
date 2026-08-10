from __future__ import annotations

from .default_loader import (
    DefaultDocumentLoader,
)
from .default_retrieval import (
    DefaultRetrieval,
)
from .default_splitter import (
    DefaultDocumentSplitter,
)
from .ingestion.pipeline import (
    DocumentIngestionPipeline,
)
from .lancedb import (
    LanceRAGStore,
)
from .provider import (
    RAGProvider,
)

_provider: RAGProvider | None = None


def create_rag_provider(namespace: str) -> RAGProvider:
    """
    Create the default RAG provider.

    The default implementation uses:

    - LanceDB for document storage
    - DefaultRetrieval for query construction
    - DefaultDocumentLoader for document loading
    - DefaultDocumentSplitter for chunking
    """

    store = LanceRAGStore(namespace=namespace)

    ingestion = DocumentIngestionPipeline(
        loader=DefaultDocumentLoader(),
        splitter=DefaultDocumentSplitter(),
        store=store,
    )

    return RAGProvider(
        store=store,
        retrieval=DefaultRetrieval(),
        ingestion=ingestion,
    )


def get_rag_provider() -> RAGProvider:
    """
    Return the shared RAG provider instance.
    """

    global _provider

    if _provider is None:
        _provider = create_rag_provider()

    return _provider
