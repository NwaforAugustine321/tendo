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
    ) -> None:

        self._embeddings = (
            embeddings
            or get_embedding_client()
        )

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
    ) -> RAGContext:

        if not query.strip():
            return RAGContext()

        vector = await self._embed_query(
            query,
        )

        rows = (
            self._table.search(vector)
            .limit(limit)
            .to_list()
        )

        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(
            f"RAG retrieve: query='{query[:50]}', rows_found={len(rows)}")

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
                for row in rows
            ]
        )

    async def add(
        self,
        *,
        documents: list[RAGDocument],
    ) -> None:

        if not documents:
            return

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
