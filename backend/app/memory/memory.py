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
    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    scope: list[str] = Field(default_factory=lambda: ["/"])
    metadata: dict[str, Any] = Field(default_factory=dict)
    images: list[str] = Field(default_factory=list)
    audio: list[str] = Field(default_factory=list)
    videos: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    embedding: list[float] | None = Field(default=None, exclude=True, repr=False)


class Memory:

    def __init__(
        self,
        scopes: list[str] | str = "/",
        storage: LanceDBStorage | None = None,
        business_id: str = "",
        table_name: str | None = None,
    ) -> None:
        if isinstance(scopes, str):
            self._scopes = [scopes.rstrip("/") or "/"]
        else:
            self._scopes = [s.rstrip("/") or "/" for s in scopes]
        self._table_name = table_name
        if storage:
            self._storage = storage
        elif business_id:
            self._storage = LanceDBStorage(business_id=business_id)
        else:
            raise ValueError("Either 'storage' or 'business_id' must be provided to Memory.")

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
        scope: str | list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        images: list[str] | None = None,
        audio: list[str] | None = None,
        videos: list[str] | None = None,
    ) -> MemoryRecord | None:
        if not content or not content.strip():
            return None

        embedding = await self._embed(content)
        if not embedding:
            return None

        # Normalize scope to a list
        if scope is None:
            effective_scopes = list(self._scopes)
        elif isinstance(scope, str):
            effective_scopes = [scope]
        else:
            effective_scopes = scope

        record = MemoryRecord(
            id=str(uuid4()),
            content=content,
            scope=effective_scopes,
            metadata=metadata or {},
            images=images or [],
            audio=audio or [],
            videos=videos or [],
            created_at=datetime.utcnow(),
            embedding=embedding,
        )

        self._storage.save_embedded([record], table_name=self._table_name)
        return record

    async def remember_many(
        self,
        contents: list[str],
        scope: str | list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        images: list[str] | None = None,
        audio: list[str] | None = None,
        videos: list[str] | None = None,
    ) -> list[MemoryRecord]:
        if not contents:
            return []

        valid_contents = [c for c in contents if c and c.strip()]
        if not valid_contents:
            return []

        embeddings = await self._embed_batch(valid_contents)

        # Normalize scope to a list
        if scope is None:
            effective_scopes = list(self._scopes)
        elif isinstance(scope, str):
            effective_scopes = [scope]
        else:
            effective_scopes = scope

        records = []
        for content, embedding in zip(valid_contents, embeddings):
            record = MemoryRecord(
                id=str(uuid4()),
                content=content,
                scope=effective_scopes,
                metadata=metadata or {},
                images=images or [],
                audio=audio or [],
                videos=videos or [],
                created_at=datetime.utcnow(),
                embedding=embedding if embedding else None,
            )
            records.append(record)

        self._storage.save_embedded(records, table_name=self._table_name)
        return records

    async def recall(
        self,
        query: str,
        limit: int = 20,
        columns: list[str] | None = None,
        filters: str | None = None
    ) -> list[MemoryRecord]:
        if not query or not query.strip():
            return []

        search_query = query
       

        query_embedding = await self._embed(search_query)
        if not query_embedding:
            return []

        raw_results = self._storage.search(
            query_embedding=query_embedding,
            query_text=search_query,
            scope_prefixes=self._scopes,
            filters=filters,
            limit=limit,
            columns=columns,
            table_name=self._table_name,
        )

        if not raw_results:
            return []

        return [record for record, _ in raw_results]


    async def fetch(
        self,
        limit: int = 10,
        filters: str | None = None,
    ) -> list[MemoryRecord]:
        """Fetch recent messages by scope without semantic search.
        
        Simply retrieves the most recent rows from the table, ordered by created_at.
        No embedding or vector similarity is used.
        """
        return self._storage.fetch(
            scope_prefixes=self._scopes,
            filters=filters,
            limit=limit,
            table_name=self._table_name,
        )

    async def save(
        self,
        content: str,
        scope: str | list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord | None:
        """Save a message as a plain row without generating an embedding.
        
        No vector embedding is computed — the row is stored with a zero vector.
        Use this for conversation messages that only need chronological retrieval.
        """
        if not content or not content.strip():
            return None

        # Normalize scope to a list
        if scope is None:
            effective_scopes = list(self._scopes)
        elif isinstance(scope, str):
            effective_scopes = [scope]
        else:
            effective_scopes = scope

        record = MemoryRecord(
            id=str(uuid4()),
            content=content,
            scope=effective_scopes,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            embedding=None,
        )

        self._storage.save(records=[record], table_name=self._table_name)
        return record

    def forget(self, scope: str | None = None) -> int:
        if scope:
            return self._storage.delete(scope_prefixes=[scope])
        return self._storage.delete(scope_prefixes=self._scopes)

    @property
    def count(self) -> int:
        return self._storage.count(scope_prefix=self._scopes[0] if self._scopes else None)
