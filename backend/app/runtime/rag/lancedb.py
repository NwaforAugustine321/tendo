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
        read_tables: list[str] | None = None,
        uri: str | Path = "./data/rag",
        embeddings: EmbeddingProvider | None = None,
        scopes: list[str] | None = None,
        ignore_threshold: bool = False
    ) -> None:

        self._embeddings = (
            embeddings
            or get_embedding_client()
        )

        self._scopes = scopes or []
        self._ignore_threshold = ignore_threshold

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

        # Write table — always a single explicit table.
        self._table = self._get_or_create_table(
            table_name,
        )

        # ------------------------------------------------------
        # Read tables — queried during retrieval.
        #
        # The write table is always readable. Additional read
        # tables are opt-in via read_tables; there is no
        # implicit default set.
        # ------------------------------------------------------

        requested_read_names = (
            list(read_tables)
            if read_tables is not None
            else []
        )

        all_read_names = list(
            dict.fromkeys(
                [table_name] + requested_read_names,
            )
        )

        self._read_table_names = all_read_names

        self._read_tables = [
            self._get_or_create_table(name)
            for name in all_read_names
        ]

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
        limit: int = 25,
        distance_threshold: float = 0.5,
        scopes: list[str] | None = None
    ) -> RAGContext:

        if not query.strip():
            return RAGContext()

        vector = await self._embed_query(
            query,
        )

        merged_scopes = list(set(self._scopes + (scopes or [])))

        # Query all read tables and merge results
        all_rows: list[dict[str, Any]] = []

        for table in self._read_tables:
            try:
                search = (
                    table.search(vector)
                    .metric("cosine")
                    .limit(limit)
                )

                if merged_scopes:
                    escaped = ", ".join(f"'{s}'" for s in merged_scopes)
                    search = search.where(
                        f"array_has_any(scopes, [{escaped}])")

                rows = search.to_list()
                all_rows.extend(rows)
            except Exception:
                continue

        # Sort by distance (lower = more similar)
        all_rows.sort(key=lambda r: r.get("_distance", 1.0))

        # Filter out results that are too far from the query
        relevant_rows = [
            row for row in all_rows
            if row.get("_distance", 1.0) <= distance_threshold
        ]

        selected_rows = all_rows if self._ignore_threshold else relevant_rows
        _logger.info(
            f"RAG retrieve: query='{query[:50]}', "
            f"rows_found={len(selected_rows)}, "
            f"tables={self._read_table_names}"
        )

        # Apply limit after merging
        selected_rows = selected_rows[:limit]

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
                for row in selected_rows
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
