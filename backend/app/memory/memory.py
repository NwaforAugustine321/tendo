from __future__ import annotations
import json
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, Field
from app.memory.lancedb import LanceDBStorage

logger = logging.getLogger(__name__)



class MemoryRecord(BaseModel):
    """A single memory entry stored in the memory system."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    scope: str = Field(default="/")
    categories: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    embedding: list[float] | None = Field(default=None, exclude=True, repr=False)
    source: str | None = Field(default=None)
    private: bool = Field(default=False)

    def format(self) -> str:
        lines = [f"- {self.content}"]
        if self.categories:
            lines.append(f"  categories: {', '.join(self.categories)}")
        return "\n".join(lines)


_storage: LanceDBStorage | None = None


def _get_storage() -> LanceDBStorage:
    global _storage
    if _storage is None:
        _storage = LanceDBStorage()
    return _storage


class Memory:

    def __init__(
        self,
        scope: str,
        storage: LanceDBStorage | None = None,
    ) -> None:
        self._scope = scope.rstrip("/") or "/"
        self._storage = storage or _get_storage()

    async def _embed(self, text: str) -> list[float]:
        from app.embeddings.client import get_embedding_client

        embedder = get_embedding_client()
        embeddings = await embedder.aembed_documents([text])
        return embeddings[0] if embeddings else []

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
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
        """Store a single item in memory."""
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
            importance=importance or 0.5,
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
        """Store multiple items in memory efficiently (single embed call)."""
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
                importance=importance or 0.5,
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
        use_query_analysis: bool = False,
    ) -> list[MemoryRecord]:
        """Retrieve relevant memories using semantic search."""
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

        raw_results = self._storage.search(
            query_embedding=query_embedding,
            scope_prefix=effective_scope,
            limit=limit,
        )

        if not raw_results:
            return []

        return [record for record, _ in raw_results]

    async def _analyze_query(self, query: str) -> str:
        """Analyze and rewrite a query using LLM for better recall."""
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
                    query=query, available_scopes=self._scope, scope_desc=""
                )},
            ]
            response = await llm.ainvoke(messages)
            raw = response.content.strip() if response.content else ""

            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            analysis = json.loads(raw)

            recall_queries = analysis.get("recall_queries", [])
            return " ".join(recall_queries) if recall_queries else query
        except Exception as e:
            logger.debug(f"Query analysis failed, using original: {e}")
            return query

    def forget(self, scope: str | None = None) -> int:
        """Delete memories in the given scope."""
        effective_scope = self._scope
        if scope:
            effective_scope = f"{self._scope}/{scope.strip('/')}"
        return self._storage.delete(scope_prefix=effective_scope)

    @property
    def count(self) -> int:
        """Get the number of records in this memory scope."""
        return self._storage.count(scope_prefix=self._scope)



