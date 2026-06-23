"""Knowledge store — semantic memory powered by ChromaDB.

Follows similar patterns to CrewAI's Knowledge class:
- add() to ingest content
- query() to search by similarity
- reset() to clear a collection

Uses the project's existing embedding client for vector generation.
"""

import logging
import uuid
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config.settings import settings

logger = logging.getLogger(__name__)

_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    """Get or create the persistent ChromaDB client."""
    global _client
    if _client is None:
        persist_dir = settings.vector_store_path
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"Knowledge store initialized at {persist_dir}")
    return _client


class Knowledge:
    """
    Knowledge store for semantic memory search and retrieval.

    Each collection groups related memories (e.g., per business or per domain).

    Usage:
        knowledge = Knowledge(collection_name="business_01d7cec4")
        await knowledge.add("Customer John prefers cash payments", metadata={...})
        results = await knowledge.query("payment preferences")
        knowledge.reset()
    """

    def __init__(self, collection_name: str = "business_memory"):
        self._collection_name = collection_name
        self._collection: chromadb.Collection | None = None

    @property
    def collection(self) -> chromadb.Collection:
        """Get or create the collection."""
        if self._collection is None:
            client = _get_client()
            self._collection = client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    async def add(
        self,
        content: str | list[str],
        metadata: dict | list[dict] | None = None,
        ids: list[str] | None = None,
    ) -> list[str]:
        """
        Add content to the knowledge store.

        Args:
            content: Text or list of texts to store.
            metadata: Optional metadata dict or list of dicts.
            ids: Optional list of document IDs. Auto-generated if not provided.

        Returns:
            List of document IDs that were stored.
        """
        from app.embeddings.client import get_embedding_client

        texts = [content] if isinstance(content, str) else content
        metadatas = [metadata or {}] if isinstance(metadata, (dict, type(None))) else metadata
        doc_ids = ids or [str(uuid.uuid4()) for _ in texts]

        # Ensure metadatas matches texts length
        if len(metadatas) == 1 and len(texts) > 1:
            metadatas = metadatas * len(texts)

        embedder = get_embedding_client()
        embeddings = await embedder.aembed_documents(texts)

        self.collection.upsert(
            ids=doc_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        logger.debug(f"Added {len(texts)} items to '{self._collection_name}'")
        return doc_ids

    async def query(
        self,
        query: str | list[str],
        n_results: int = 5,
        score_threshold: float = 0.6,
        where: dict | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query the knowledge store for similar content.

        Args:
            query: Search query string or list of queries.
            n_results: Maximum number of results to return.
            score_threshold: Minimum similarity score (0-1, lower distance = more similar).
            where: Optional metadata filter.

        Returns:
            List of results with {id, text, metadata, score}.
        """
        from app.embeddings.client import get_embedding_client

        queries = [query] if isinstance(query, str) else query
        embedder = get_embedding_client()
        query_embeddings = await embedder.aembed_documents(queries)

        results = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where,
        )

        items = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else 1.0
                # ChromaDB returns distance (lower = more similar), convert to score
                score = 1.0 - distance
                if score >= score_threshold:
                    items.append({
                        "id": results["ids"][0][i] if results["ids"] else "",
                        "text": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "score": score,
                    })

        return items

    def reset(self) -> None:
        """Delete all items in the collection."""
        client = _get_client()
        try:
            client.delete_collection(self._collection_name)
            self._collection = None
            logger.info(f"Reset knowledge collection: {self._collection_name}")
        except Exception as e:
            logger.warning(f"Failed to reset collection: {e}")

    async def delete(self, ids: list[str]) -> None:
        """Delete specific items by ID."""
        self.collection.delete(ids=ids)
        logger.debug(f"Deleted {len(ids)} items from '{self._collection_name}'")

    @property
    def count(self) -> int:
        """Get the number of items in the collection."""
        return self.collection.count()
