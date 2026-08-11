from __future__ import annotations

import json
from datetime import datetime, UTC
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

from .context import MemoryContext
from .models import MemoryEntry
from .reflection import MemoryReflection
from .store import MemoryStore
import logging

_logger = logging.getLogger(__name__)


def _create_memory_schema(
    dimension: int,
) -> type[LanceModel]:
    """
    Create a LanceDB schema using the configured
    embedding dimension.
    """

    class MemoryRecord(LanceModel):
        id: str

        text: str

        category: str = "general"

        metadata: str = Field(
            default="{}",
        )

        created_at: datetime

        vector: Vector(dimension)

    return MemoryRecord


class LanceMemoryStore(
    MemoryStore,
):
    """
    LanceDB implementation of MemoryStore.
    """

    def __init__(
        self,
        *,
        db: lancedb.DBConnection | None = None,
        namespace: str,
        table_name: str = "memory",
        uri: str | Path = "./data/memory",
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

        self._schema = _create_memory_schema(
            self._embeddings.dimension,
        )

        self._table = self._get_or_create_table(
            table_name,
        )

    def _get_or_create_table(
        self,
        table_name: str,
    ) -> lancedb.table.Table:

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
    ) -> MemoryContext:

        if not query.strip():
            return MemoryContext()

        vector = await self._embeddings.embed(
            query,
        )

        rows = (
            self._table.search(vector)
            .metric("cosine")
            .limit(limit)
            .to_list()
        )

        # Filter out results that are too far from the query
        # Cosine distance: 0 = identical, ~0.6-0.7 = somewhat related, >1.0 = unrelated
        relevant_rows = [
            row for row in rows
            if row.get("_distance", 1.0) <= distance_threshold
        ]

        _logger.info(
            f"Mem retrieve: query='{query[:50]}', "
            f"rows_found={len(rows)}, "
        )

        return MemoryContext(
            entries=[
                MemoryEntry(
                    id=row["id"],
                    text=row["text"],
                    category=row["category"],
                    metadata=json.loads(
                        row.get("metadata", "{}"),
                    ),
                )
                for row in relevant_rows
            ]
        )

    async def save(
        self,
        *,
        reflection: MemoryReflection,
    ) -> None:

        if reflection.empty:
            return

        await self._insert(
            reflection.entries,
        )

    async def delete(
        self,
        *,
        memory_id: str,
    ) -> None:

        self._table.delete(
            f"id='{memory_id}'",
        )

    async def _insert(
        self,
        entries: list[MemoryEntry],
    ) -> None:

        # Dedup: only insert entries that don't already
        # have a semantically similar match in the store.
        unique_entries = []
        unique_vectors = []

        vectors = await self._embeddings.embed_documents(
            [
                entry.text
                for entry in entries
            ]
        )

        for entry, vector in zip(entries, vectors):

            if self._is_duplicate(vector):
                continue

            unique_entries.append(entry)
            unique_vectors.append(vector)

        if not unique_entries:
            return

        rows = [
            self._schema(
                id=entry.id or str(uuid4()),
                text=entry.text,
                category=entry.category,
                metadata=json.dumps(entry.metadata),
                created_at=datetime.now(UTC),
                vector=vector,
            )
            for entry, vector in zip(
                unique_entries,
                unique_vectors,
            )
        ]

        self._table.add(
            rows,
        )

    def _is_duplicate(
        self,
        vector: list[float],
        threshold: float = 0.92,
    ) -> bool:
        """
        Check if a semantically similar memory already exists.
        Returns True if a match with cosine similarity >= threshold is found.
        """

        try:
            results = (
                self._table.search(vector)
                .metric("cosine")
                .limit(1)
                .to_list()
            )

            if not results:
                return False

            distance = results[0].get("_distance", 1.0)

            # Cosine distance: 0 = identical, 1 = completely different.
            # similarity = 1 - distance
            # We want: similarity >= threshold → distance <= (1 - threshold)
            return distance <= (1.0 - threshold)

        except Exception:
            return False

    async def _update(
        self,
        entry: MemoryEntry,
    ) -> None:

        vector = await self._embeddings.embed(
            entry.text,
        )

        self._table.update(
            where=f"id='{entry.id}'",
            values={
                "text": entry.text,
                "category": entry.category,
                "metadata": json.dumps(entry.metadata),
                "created_at": datetime.now(UTC),
                "vector": vector,
            },
        )
