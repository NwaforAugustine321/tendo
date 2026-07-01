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
        use_query_analysis: bool = False,
    ) -> list[MemoryMatch]:
        """Retrieve relevant memories using semantic search with composite scoring and reranking.

        Args:
            query: Natural language query.
            limit: Maximum number of results.
            scope: Optional sub-scope to search within.
            min_score: Minimum composite score threshold.
            use_query_analysis: If True, use LLM to analyze and rewrite query (Req 6).

        Returns:
            List of MemoryMatch, ordered by composite relevance score.
        """
        if not query or not query.strip():
            return []

    
        search_query = query
        if use_query_analysis:
            search_query = await self._analyze_query(query)

        query_embedding = await self._embed(search_query)
        if not query_embedding:
            return []

        effective_scope = self._scope
        if scope:
            effective_scope = f"{self._scope}/{scope.strip('/')}"

        # Fetch a large initial set (100) for reranking
        fetch_count = max(100, limit * 10)
        raw_results = self._storage.search(
            query_embedding=query_embedding,
            scope_prefix=effective_scope,
            limit=fetch_count,
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

        # Rerank using  reranker for better relevance
        if len(matches) > limit:
            try:
                from app.embeddings.reranker import rerank_results
                documents = [m.record.content for m in matches]
                reranked_texts = rerank_results(query=search_query, documents=documents, top_k=limit)
                
                # Rebuild matches in reranked order
                content_to_match = {m.record.content: m for m in matches}
                reranked_matches = []
                for text in reranked_texts:
                    if text in content_to_match:
                        reranked_matches.append(content_to_match[text])
                
                if reranked_matches:
                    return reranked_matches
            except Exception as e:
                logger.debug(f"Reranking skipped: {e}")

        return matches[:limit]

    async def _analyze_query(self, query: str) -> str:
        """Analyze and rewrite a query using memory.query_system/query_user prompts (Req 6)."""
        import json
        from app.lib.i18n import _get_i18n
        from app.llm.client import get_client

        i18n = _get_i18n()
        system_prompt = i18n.get("memory.query_system")
        user_template = i18n.get("memory.query_user")

        if not system_prompt or not user_template:
            return query

        try:
            llm = get_client()
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_template.format(
                    query=query,
                    available_scopes=self._scope,
                    scope_desc="",
                )},
            ]
            response = await llm.ainvoke(messages)
            raw = response.content.strip() if response.content else ""

            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            analysis = json.loads(raw)

            # Use the recall_queries if available
            recall_queries = analysis.get("recall_queries", [])
            if recall_queries:
                return " ".join(recall_queries)
            return query
        except Exception as e:
            logger.debug(f"Query analysis failed, using original: {e}")
            return query

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

    # --- Req 7: Extract memories from conversation ---
    async def extract_and_remember(self, conversation_content: str) -> list[MemoryRecord]:
        """Extract discrete facts from a conversation and store them.

        Uses memory.extract_memories_system/user i18n prompts to LLM-extract
        reusable memory statements from raw conversation content.

        Args:
            conversation_content: The raw conversation text to extract from.

        Returns:
            List of stored MemoryRecords (empty if nothing worth storing).
        """
        import json
        from app.lib.i18n import _get_i18n
        from app.llm.client import get_client

        i18n = _get_i18n()
        system_prompt = i18n.get("memory.extract_memories_system")
        user_template = i18n.get("memory.extract_memories_user")

        if not system_prompt or not user_template:
            return []

        try:
            llm = get_client()
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_template.format(content=conversation_content)},
            ]
            response = await llm.ainvoke(messages)
            content = response.content.strip() if response.content else ""

            # Parse JSON response
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(content)
            memories = data.get("memories", [])

            if not memories:
                return []

            return await self.remember_many(memories, source="auto_extraction")
        except Exception as e:
            logger.warning(f"Memory extraction failed: {e}")
            return []

    async def remember_with_analysis(
        self,
        content: str,
        existing_scopes: list[str] | None = None,
        existing_categories: list[str] | None = None,
    ) -> MemoryRecord | None:
        """Save content with LLM-analyzed scope, categories, and importance.

        Args:
            content: Text to remember.
            existing_scopes: Available scope paths for context.
            existing_categories: Available categories for context.

        Returns:
            The stored MemoryRecord with LLM-determined metadata.
        """
        import json
        from app.lib.i18n import _get_i18n
        from app.llm.client import get_client

        i18n = _get_i18n()
        system_prompt = i18n.get("memory.save_system")
        user_template = i18n.get("memory.save_user")

        if not system_prompt or not user_template:
            return await self.remember(content)

        try:
            llm = get_client()
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_template.format(
                    content=content,
                    existing_scopes=", ".join(existing_scopes or [self._scope]),
                    existing_categories=", ".join(existing_categories or []),
                )},
            ]
            response = await llm.ainvoke(messages)
            raw = response.content.strip() if response.content else ""

            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            analysis = json.loads(raw)

            return await self.remember(
                content=content,
                scope=analysis.get("suggested_scope"),
                categories=analysis.get("categories"),
                metadata=analysis.get("extracted_metadata"),
                importance=analysis.get("importance"),
            )
        except Exception as e:
            logger.warning(f"Memory save analysis failed, saving without analysis: {e}")
            return await self.remember(content)

    async def remember_with_consolidation(self, content: str) -> MemoryRecord | None:
        """Store content with deduplication/consolidation against existing memories.

        Args:
            content: Text to remember.

        Returns:
            The stored MemoryRecord, or None if consolidated into existing.
        """
        import json
        from app.lib.i18n import _get_i18n
        from app.llm.client import get_client

        i18n = _get_i18n()
        system_prompt = i18n.get("memory.consolidation_system")
        user_template = i18n.get("memory.consolidation_user")

        if not system_prompt or not user_template:
            return await self.remember(content)

        # Find similar existing memories
        similar = await self.recall(content, limit=5)
        if not similar:
            return await self.remember(content)

        # Build summary of existing records
        records_summary = "\n".join(
            f"- ID: {m.record.id} | Content: {m.record.content[:200]}"
            for m in similar
        )

        try:
            llm = get_client()
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_template.format(
                    new_content=content,
                    records_summary=records_summary,
                )},
            ]
            response = await llm.ainvoke(messages)
            raw = response.content.strip() if response.content else ""

            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            plan = json.loads(raw)

            # Execute consolidation plan
            actions = plan.get("actions", plan.get("existing_memories", []))
            for action in actions:
                record_id = action.get("id", "")
                op = action.get("action", "keep")
                if op == "delete" and record_id:
                    self._storage.delete_by_id(record_id)
                elif op == "update" and record_id:
                    updated_content = action.get("content", action.get("updated_content", ""))
                    if updated_content:
                        self._storage.delete_by_id(record_id)
                        await self.remember(updated_content)

            # Insert new if plan says so
            insert_new = plan.get("insert_new", True)
            if insert_new:
                return await self.remember(content)
            return None

        except Exception as e:
            logger.warning(f"Memory consolidation failed, saving directly: {e}")
            return await self.remember(content)
