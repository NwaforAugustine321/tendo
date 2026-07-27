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
    scope: str = Field(default="/")
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
    ) -> None:
        if isinstance(scopes, str):
            self._scopes = [scopes.rstrip("/") or "/"]
        else:
            self._scopes = [s.rstrip("/") or "/" for s in scopes]
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
        scope: str | None = None,
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

        effective_scope = scope or self._scopes[0]

        record = MemoryRecord(
            id=str(uuid4()),
            content=content,
            scope=effective_scope,
            metadata=metadata or {},
            images=images or [],
            audio=audio or [],
            videos=videos or [],
            created_at=datetime.utcnow(),
            embedding=embedding,
        )

        self._storage.save([record])
        return record

    async def remember_many(
        self,
        contents: list[str],
        scope: str | None = None,
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

        effective_scope = scope or self._scopes[0]

        records = []
        for content, embedding in zip(valid_contents, embeddings):
            record = MemoryRecord(
                id=str(uuid4()),
                content=content,
                scope=effective_scope,
                metadata=metadata or {},
                images=images or [],
                audio=audio or [],
                videos=videos or [],
                created_at=datetime.utcnow(),
                embedding=embedding if embedding else None,
            )
            records.append(record)

        self._storage.save(records)
        return records

    async def recall(
        self,
        query: str,
        limit: int = 5,
        columns: list[str] | None = None,
        filters: str | None = None,
        use_query_analysis: bool = False,
    ) -> list[MemoryRecord]:
        if not query or not query.strip():
            return []

        search_query = query
        if use_query_analysis:
            search_query = await self._analyze_query(query)

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
        )

        if not raw_results:
            return []

        return [record for record, _ in raw_results]

    async def _analyze_query(self, query: str) -> str:
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
                    query=query, available_scopes=", ".join(self._scopes), scope_desc=""
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
        if scope:
            return self._storage.delete(scope_prefixes=[scope])
        return self._storage.delete(scope_prefixes=self._scopes)

    @property
    def count(self) -> int:
        return self._storage.count(scope_prefix=self._scopes[0] if self._scopes else None)
