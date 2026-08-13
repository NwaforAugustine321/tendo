from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import lancedb
from lancedb.pydantic import LanceModel, Vector
from pydantic import Field

from app.runtime.embeddings.client import (
    get_embedding_client,
)
from app.runtime.embeddings.provider import (
    EmbeddingProvider,
)

from .context import RAGContext
from .models import RAGDocument
from .store import RAGStore
import logging

_logger = logging.getLogger(__name__)


def create_rag_schema(
    dimension: int,
) -> type[LanceModel]:
    """
    Create the LanceDB schema for knowledge documents.
    """

    class RAGRecord(LanceModel):
        id: str

        parent_id: str = ""

        title: str = ""

        content: str

        source: str = ""

        scopes: list[str] = Field(default_factory=list)

        metadata: str = Field(
            default="{}",
        )

        created_at: datetime

        updated_at: datetime

        vector: Vector(dimension)

    return RAGRecord


class LanceRAGStore(
    RAGStore,
):
    """
    LanceDB implementation of a RAG knowledge store.
    """

    def __init__(
        self,
        *,
        db: lancedb.DBConnection | None = None,
        namespace: str,
        table_name: str = "knowledge",
        uri: str | Path = "./data/rag",
        embeddings: EmbeddingProvider | None = None,
        scopes: list[str] | None = None,
    ) -> None:

        self._embeddings = (
            embeddings
            or get_embedding_client()
        )

        self._scopes = scopes or []

        self._db = (
            db
            or lancedb.connect(
                str(
                    Path(uri) / namespace
                )
            )
        )

        self._schema = create_rag_schema(
            self._embeddings.dimension,
        )

        self._table = self._get_or_create_table(
            table_name,
        )

    def _get_or_create_table(
        self,
        table_name: str,
    ):

        if table_name in self._db.table_names():

            return self._db.open_table(
                table_name,
            )

        return self._db.create_table(
            table_name,
            schema=self._schema,
        )

    async def retrieve(
        self,
        *,
        query: str,
        limit: int = 5,
        distance_threshold: float = 0.75,
        scopes: list[str] | None = None,
    ) -> RAGContext:

        if not query.strip():
            return RAGContext()

        vector = await self._embed_query(
            query,
        )

        merged_scopes = list(set(self._scopes + (scopes or [])))

        rows = (
            self._table.search(vector)
            .metric("cosine")
            .limit(limit)
        )

        if merged_scopes:
            escaped = ", ".join(f"'{s}'" for s in merged_scopes)
            rows = rows.where(f"array_has_any(scopes, [{escaped}])")

        rows = rows.to_list()

        # Filter out results that are too far from the query
        # Cosine distance: 0 = identical, ~0.6-0.7 = somewhat related, >1.0 = unrelated
        relevant_rows = [
            row for row in rows
            if row.get("_distance", 1.0) <= distance_threshold
        ]

        _logger.info(
            f"RAG retrieve: query='{query[:50]}', "
            f"rows_found={len(rows)}, "

        )

        return RAGContext(
            documents=[
                RAGDocument(
                    id=row["id"],
                    parent_id=row.get(
                        "parent_id",
                        "",
                    ),
                    title=row["title"],
                    content=row["content"],
                    source=row["source"],
                    metadata=json.loads(
                        row.get("metadata", "{}"),
                    ),
                )
                for row in relevant_rows
            ]
        )

    async def add(
        self,
        *,
        documents: list[RAGDocument],
        scopes: list[str] | None = None,
    ) -> None:

        if not documents:
            return

        merged_scopes = list(set(self._scopes + (scopes or [])))

        vectors = await self._embed_documents(
            [
                document.content
                for document in documents
            ]
        )

        now = datetime.utcnow()

        rows = []

        for document, vector in zip(
            documents,
            vectors,
        ):

            rows.append(
                self._schema(
                    id=document.id
                    or str(uuid4()),
                    parent_id=document.parent_id,
                    title=document.title,
                    content=document.content,
                    source=document.source,
                    scopes=merged_scopes,
                    metadata=json.dumps(
                        document.metadata,
                    ),
                    created_at=now,
                    updated_at=now,
                    vector=vector,
                )
            )

        self._table.add(
            rows,
        )

    async def index(
        self,
        *,
        documents: list[RAGDocument],
    ) -> None:

        await self.add(
            documents=documents,
        )

    async def delete(
        self,
        *,
        document_id: str,
    ) -> None:

        self._table.delete(
            f"id='{document_id}'",
        )

    async def _embed_query(
        self,
        query: str,
    ) -> list[float]:

        return await self._embeddings.embed(
            query,
        )

    async def _embed_documents(
        self,
        documents: list[str],
    ) -> list[list[float]]:

        return await self._embeddings.embed_documents(
            documents,
        )
