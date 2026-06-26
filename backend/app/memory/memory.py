"""Unified Memory class — LanceDB-backed conversation memory with composite scoring.

Stores conversation messages (user + AI) as embedded vectors.
Retrieves relevant past messages via semantic search with recency and importance weighting.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.memory.lancedb_storage import LanceDBStorage
from app.memory.types import (
    MemoryConfig,
    MemoryMatch,
    MemoryRecord,
    compute_composite_score,
)

logger = logging.getLogger(__name__)

# Shared storage instance — all Memory instances use the same LanceDB connection
_storage: LanceDBStorage | None = None


def _get_storage() -> LanceDBStorage:
    """Get or create the shared LanceDB storage instance."""
    global _storage
    if _storage is None:
        _storage = LanceDBStorage()
    return _storage


_memory_cache: dict[str, "Memory"] = {}


def get_memory(scope: str) -> "Memory":
    """Get a cached Memory instance for a given scope.

    Avoids recreating Memory objects on every node invocation.

    Args:
        scope: The scope path (e.g., "/business/{business_id}").

    Returns:
        A cached Memory instance.
    """
    if scope not in _memory_cache:
        _memory_cache[scope] = Memory(scope=scope)
    return _memory_cache[scope]


class Memory:
    """Unified conversation memory backed by LanceDB.

    Stores messages as embedded vectors with metadata (scope, importance, source).
    Retrieves relevant memories using composite scoring: semantic + recency + importance.

    Usage:
        memory = Memory(scope=f"/business/{business_id}")
        await memory.remember("Customer prefers cash payments", importance=0.8)
        matches = await memory.recall("payment preferences", limit=5)
        for m in matches:
            print(m.format())
    """

    def __init__(
        self,
        scope: str = "/",
        config: MemoryConfig | None = None,
        storage: LanceDBStorage | None = None,
    ) -> None:
        """Initialize memory.

        Args:
            scope: Root scope for this memory instance (e.g., "/business/{id}").
            config: Scoring configuration. Defaults to standard weights.
            storage: LanceDB storage instance. Uses shared singleton if None.
        """
        self._scope = scope.rstrip("/") or "/"
        self._config = config or MemoryConfig()
        self._storage = storage or _get_storage()

    async def _embed(self, text: str) -> list[float]:
        """Embed a single text using the project's embedding client."""
        from app.embeddings.client import get_embedding_client

        embedder = get_embedding_client()
        embeddings = await embedder.aembed_documents([text])
        return embeddings[0] if embeddings else []

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single API call."""
        from app.embeddings.client import get_embedding_client

        embedder = get_embedding_client()
        return await embedder.aembed_documents(texts)

    async def remember(
        self,
        content: str,
        scope: str | None = None,
        categories: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        importance: float | None = None,
        source: str | None = None,
    ) -> MemoryRecord | None:
        """Store a single item in memory.

        Args:
            content: Text to remember.
            scope: Optional sub-scope (nested under root scope).
            categories: Optional categories/tags.
            metadata: Optional metadata dict.
            importance: Optional importance 0-1.
            source: Optional provenance identifier.

        Returns:
            The created MemoryRecord, or None on failure.
        """
        if not content or not content.strip():
            return None

        embedding = await self._embed(content)
        if not embedding:
            logger.warning("Failed to embed content for memory save")
            return None

        effective_scope = self._scope
        if scope:
            effective_scope = f"{self._scope}/{scope.strip('/')}"

        record = MemoryRecord(
            id=str(uuid4()),
            content=content,
            scope=effective_scope,
            categories=categories or [],
            metadata=metadata or {},
            importance=importance or self._config.default_importance,
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            embedding=embedding,
            source=source,
        )

        self._storage.save([record])
        logger.debug(f"Memory saved: {content[:50]}...")
        return record

    async def remember_many(
        self,
        contents: list[str],
        scope: str | None = None,
        categories: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        importance: float | None = None,
        source: str | None = None,
    ) -> list[MemoryRecord]:
        """Store multiple items in memory.

        Args:
            contents: List of text items to remember.
            scope: Optional sub-scope.
            categories: Optional categories for all items.
            metadata: Optional metadata for all items.
            importance: Optional importance for all items.
            source: Optional provenance identifier.

        Returns:
            List of created MemoryRecords.
        """
        if not contents:
            return []

        valid_contents = [c for c in contents if c and c.strip()]
        if not valid_contents:
            return []

        embeddings = await self._embed_batch(valid_contents)

        effective_scope = self._scope
        if scope:
            effective_scope = f"{self._scope}/{scope.strip('/')}"

        records = []
        for content, embedding in zip(valid_contents, embeddings):
            record = MemoryRecord(
                id=str(uuid4()),
                content=content,
                scope=effective_scope,
                categories=categories or [],
                metadata=metadata or {},
                importance=importance or self._config.default_importance,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                embedding=embedding if embedding else None,
                source=source,
            )
            records.append(record)

        self._storage.save(records)
        logger.debug(f"Memory saved {len(records)} items")
        return records

    async def recall(
        self,
        query: str,
        limit: int = 5,
        scope: str | None = None,
        min_score: float = 0.0,
    ) -> list[MemoryMatch]:
        """Retrieve relevant memories using semantic search with composite scoring.

        Args:
            query: Natural language query.
            limit: Maximum number of results.
            scope: Optional sub-scope to search within.
            min_score: Minimum composite score threshold.

        Returns:
            List of MemoryMatch, ordered by composite relevance score.
        """
        if not query or not query.strip():
            return []

        query_embedding = await self._embed(query)
        if not query_embedding:
            return []

        effective_scope = self._scope
        if scope:
            effective_scope = f"{self._scope}/{scope.strip('/')}"

        raw_results = self._storage.search(
            query_embedding=query_embedding,
            scope_prefix=effective_scope,
            limit=limit * 2,
            min_score=0.0,
        )

        if not raw_results:
            return []

        # Apply composite scoring
        matches: list[MemoryMatch] = []
        for record, semantic_score in raw_results:
            composite, reasons = compute_composite_score(
                record, semantic_score, self._config
            )
            if composite >= min_score:
                matches.append(
                    MemoryMatch(
                        record=record,
                        score=composite,
                        match_reasons=reasons,
                    )
                )

        # Sort by composite score descending
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:limit]

    def forget(self, scope: str | None = None) -> int:
        """Delete memories in the given scope.

        Args:
            scope: Optional sub-scope to delete. If None, deletes all under root scope.

        Returns:
            Number of records deleted.
        """
        effective_scope = self._scope
        if scope:
            effective_scope = f"{self._scope}/{scope.strip('/')}"
        return self._storage.delete(scope_prefix=effective_scope)

    @property
    def count(self) -> int:
        """Get the number of records in this memory scope."""
        return self._storage.count(scope_prefix=self._scope)
