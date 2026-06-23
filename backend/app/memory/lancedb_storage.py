"""LanceDB storage backend for the conversation memory system."""

from __future__ import annotations

from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any

import lancedb

from app.config.settings import settings
from app.memory.types import MemoryRecord

logger = logging.getLogger(__name__)

DEFAULT_VECTOR_DIM = 768  # Matches common embedding models


class LanceDBStorage:
    """LanceDB-backed storage for conversation memory."""

    def __init__(
        self,
        path: str | Path | None = None,
        table_name: str = "memories",
        vector_dim: int | None = None,
    ) -> None:
        """Initialize LanceDB storage.

        Args:
            path: Directory path for the LanceDB database.
            table_name: Name of the table for memory records.
            vector_dim: Dimensionality of the embedding vector.
        """
        if path is None:
            path = Path(settings.vector_store_path) / "lancedb"
        self._path = Path(path)
        self._path.mkdir(parents=True, exist_ok=True)
        self._table_name = table_name
        self._db = lancedb.connect(str(self._path))
        self._vector_dim = vector_dim or 0

        # Try to open existing table
        try:
            self._table: Any = self._db.open_table(self._table_name)
            self._vector_dim = self._infer_dim_from_table(self._table)
        except Exception:
            self._table = None
            if vector_dim:
                self._vector_dim = vector_dim
                self._table = self._create_table(vector_dim)

    @staticmethod
    def _infer_dim_from_table(table: Any) -> int:
        """Read vector dimension from an existing table's schema."""
        schema = table.schema
        for field in schema:
            if field.name == "vector":
                try:
                    return int(field.type.list_size)
                except Exception:
                    break
        return DEFAULT_VECTOR_DIM

    def _create_table(self, vector_dim: int) -> Any:
        """Create a new table with the given vector dimension."""
        placeholder = [
            {
                "id": "__schema_placeholder__",
                "content": "",
                "scope": "/",
                "categories_str": "[]",
                "metadata_str": "{}",
                "importance": 0.5,
                "created_at": datetime.utcnow().isoformat(),
                "last_accessed": datetime.utcnow().isoformat(),
                "source": "",
                "private": False,
                "vector": [0.0] * vector_dim,
            }
        ]
        try:
            table = self._db.create_table(self._table_name, placeholder)
        except ValueError:
            table = self._db.open_table(self._table_name)
        else:
            table.delete("id = '__schema_placeholder__'")
        return table

    def _ensure_table(self, vector_dim: int | None = None) -> Any:
        """Return the table, creating it lazily if needed."""
        if self._table is not None:
            return self._table
        dim = vector_dim or self._vector_dim or DEFAULT_VECTOR_DIM
        self._vector_dim = dim
        self._table = self._create_table(dim)
        return self._table

    def _record_to_row(self, record: MemoryRecord) -> dict[str, Any]:
        return {
            "id": record.id,
            "content": record.content,
            "scope": record.scope,
            "categories_str": json.dumps(record.categories),
            "metadata_str": json.dumps(record.metadata),
            "importance": record.importance,
            "created_at": record.created_at.isoformat(),
            "last_accessed": record.last_accessed.isoformat(),
            "source": record.source or "",
            "private": record.private,
            "vector": record.embedding
            if record.embedding
            else [0.0] * self._vector_dim,
        }

    def _row_to_record(self, row: dict[str, Any]) -> MemoryRecord:
        def _parse_dt(val: Any) -> datetime:
            if val is None:
                return datetime.utcnow()
            if isinstance(val, datetime):
                return val
            return datetime.fromisoformat(str(val).replace("Z", "+00:00"))

        return MemoryRecord(
            id=str(row["id"]),
            content=str(row["content"]),
            scope=str(row["scope"]),
            categories=json.loads(row["categories_str"])
            if row.get("categories_str")
            else [],
            metadata=json.loads(row["metadata_str"]) if row.get("metadata_str") else {},
            importance=float(row.get("importance", 0.5)),
            created_at=_parse_dt(row.get("created_at")),
            last_accessed=_parse_dt(row.get("last_accessed")),
            embedding=row.get("vector"),
            source=row.get("source") or None,
            private=bool(row.get("private", False)),
        )

    def save(self, records: list[MemoryRecord]) -> None:
        """Save memory records to storage."""
        if not records:
            return
        # Auto-detect dimension from the first real embedding
        dim = None
        for r in records:
            if r.embedding and len(r.embedding) > 0:
                dim = len(r.embedding)
                break
        self._ensure_table(vector_dim=dim)
        rows = [self._record_to_row(rec) for rec in records]
        for row in rows:
            if row["vector"] is None or len(row["vector"]) != self._vector_dim:
                row["vector"] = [0.0] * self._vector_dim
        self._table.add(rows)

    def search(
        self,
        query_embedding: list[float],
        scope_prefix: str | None = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[tuple[MemoryRecord, float]]:
        """Search for memories by vector similarity."""
        if self._table is None:
            return []

        query = self._table.search(query_embedding)
        if scope_prefix is not None and scope_prefix.strip("/"):
            prefix = scope_prefix.rstrip("/")
            query = query.where(f"scope LIKE '{prefix}%'")

        results = query.limit(limit * 2).to_list()

        out: list[tuple[MemoryRecord, float]] = []
        for row in results:
            record = self._row_to_record(row)
            distance = row.get("_distance", 0.0)
            score = 1.0 / (1.0 + float(distance)) if distance is not None else 1.0
            if score >= min_score:
                out.append((record, score))
            if len(out) >= limit:
                break
        return out[:limit]

    def delete(
        self,
        scope_prefix: str | None = None,
        record_ids: list[str] | None = None,
    ) -> int:
        """Delete memories matching the given criteria."""
        if self._table is None:
            return 0
        if record_ids:
            before = int(self._table.count_rows())
            ids_expr = ", ".join(f"'{rid}'" for rid in record_ids)
            self._table.delete(f"id IN ({ids_expr})")
            return before - int(self._table.count_rows())
        if scope_prefix:
            prefix = scope_prefix.rstrip("/")
            before = int(self._table.count_rows())
            self._table.delete(f"scope LIKE '{prefix}%'")
            return before - int(self._table.count_rows())
        before = int(self._table.count_rows())
        self._table.delete("id != ''")
        return before

    def count(self, scope_prefix: str | None = None) -> int:
        """Count records in scope."""
        if self._table is None:
            return 0
        return int(self._table.count_rows())

    def reset(self) -> None:
        """Reset (delete all) memories."""
        if self._table is not None:
            self._db.drop_table(self._table_name)
        self._table = None
