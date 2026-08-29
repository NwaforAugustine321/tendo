from __future__ import annotations

from .ingestion.default_loader import (
    DefaultDocumentLoader,
)
from .default_retrieval import (
    DefaultRetrieval,
)
from .ingestion.default_splitter import (
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


def create_rag_provider(namespace: str, scopes: list[str] | None = None, ignore_threshold: bool = False) -> RAGProvider:
    """
    Create the default RAG provider.

    The default implementation uses:

    - LanceDB for document storage
    - DefaultRetrieval for query construction
    - DefaultDocumentLoader for document loading
    - DefaultDocumentSplitter for chunking
    """

    ingestion = DocumentIngestionPipeline(
        loader=DefaultDocumentLoader(),
        splitter=DefaultDocumentSplitter(),
        store=LanceRAGStore(namespace=namespace, scopes=scopes),
    )

    return RAGProvider(
        store=LanceRAGStore(namespace=namespace, scopes=scopes,
                            ignore_threshold=ignore_threshold),
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
