from __future__ import annotations
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import lancedb
import pyarrow as pa

from app.config.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_VECTOR_DIM = 768
TABLE_NAME = "knowledge"
CONVERSATIONS_TABLE_NAME = "conversations"


def _build_schema(vector_dim: int) -> pa.Schema:
    return pa.schema([
        pa.field("id", pa.string()),
        pa.field("content", pa.string()),
        pa.field("scope", pa.string()),
        pa.field("metadata", pa.string()),
        pa.field("images", pa.list_(pa.binary())),
        pa.field("audio", pa.list_(pa.binary())),
        pa.field("videos", pa.list_(pa.large_binary())),
        pa.field("created_at", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), vector_dim)),
    ])


class LanceDBStorage:

    def __init__(
        self,
        *,
        business_id: str,
        path: str | Path | None = None,
        vector_dim: int | None = None,
    ) -> None:
        if path is None:
            path = Path(settings.vector_store_path) / "lancedb"
        self._path = Path(path) / business_id
        self._path.mkdir(parents=True, exist_ok=True)
        self._business_id = business_id
        self._vector_dim = vector_dim or 0

        self._db = lancedb.connect(str(self._path))

        # Knowledge table
        try:
            self._table: Any = self._db.open_table(TABLE_NAME)
            self._vector_dim = self._infer_dim(self._table)
        except Exception:
            self._table = None
            if vector_dim:
                self._vector_dim = vector_dim
                self._table = self._create_table(TABLE_NAME, vector_dim)

        # Conversations table (auto-created alongside knowledge)
        try:
            self._conversations_table: Any = self._db.open_table(CONVERSATIONS_TABLE_NAME)
        except Exception:
            dim = self._vector_dim or DEFAULT_VECTOR_DIM
            self._conversations_table = self._create_table(CONVERSATIONS_TABLE_NAME, dim)

        self._ensure_fts_index()

    @staticmethod
    def _infer_dim(table: Any) -> int:
        schema = table.schema
        for field in schema:
            if field.name == "vector":
                try:
                    return int(field.type.list_size)
                except Exception:
                    break
        return DEFAULT_VECTOR_DIM

    def _ensure_fts_index(self) -> None:
        if self._table is None:
            return
        try:
            self._table.create_fts_index("content", replace=False)
        except Exception:
            pass

    def _create_table(self, name: str, vector_dim: int) -> Any:
        schema = _build_schema(vector_dim)
        placeholder = [
            {
                "id": "__schema_placeholder__",
                "content": "",
                "scope": "/",
                "metadata": "{}",
                "images": [],
                "audio": [],
                "videos": [],
                "created_at": datetime.utcnow().isoformat(),
                "vector": [0.0] * vector_dim,
            }
        ]
        try:
            table = self._db.create_table(name, data=placeholder, schema=schema)
        except (ValueError, Exception):
            try:
                table = self._db.open_table(name)
            except Exception:
                return None
        else:
            table.delete("id = '__schema_placeholder__'")
        return table

    def _ensure_table(self, vector_dim: int | None = None) -> Any:
        if self._table is not None:
            return self._table
        dim = vector_dim or self._vector_dim or DEFAULT_VECTOR_DIM
        self._vector_dim = dim
        self._table = self._create_table(TABLE_NAME, dim)
        return self._table

    def _ensure_conversations_table(self, vector_dim: int | None = None) -> Any:
        if self._conversations_table is not None:
            return self._conversations_table
        dim = vector_dim or self._vector_dim or DEFAULT_VECTOR_DIM
        self._conversations_table = self._create_table(CONVERSATIONS_TABLE_NAME, dim)
        return self._conversations_table

    def get_table(self, table_name: str | None = None) -> Any:
        """Get the appropriate table by name."""
        if table_name == CONVERSATIONS_TABLE_NAME:
            return self._conversations_table
        return self._table

    def _record_to_row(self, record: Any) -> dict[str, Any]:
        metadata = record.metadata
        if isinstance(metadata, dict):
            metadata = json.dumps(metadata)
        elif metadata is None:
            metadata = "{}"

        return {
            "id": record.id,
            "content": record.content,
            "scope": record.scope,
            "metadata": metadata,
            "images": self._to_bytes_list(record.images) if record.images else [],
            "audio": self._to_bytes_list(record.audio) if record.audio else [],
            "videos": self._to_bytes_list(record.videos) if record.videos else [],
            "created_at": record.created_at.isoformat() if isinstance(record.created_at, datetime) else str(record.created_at),
            "vector": record.embedding if record.embedding else [0.0] * self._vector_dim,
        }

    @staticmethod
    def _to_bytes_list(items: list) -> list[bytes]:
        result = []
        for item in items:
            if isinstance(item, bytes):
                result.append(item)
            elif isinstance(item, str):
                result.append(item.encode("utf-8"))
            else:
                result.append(str(item).encode("utf-8"))
        return result

    @staticmethod
    def _from_bytes_list(items: Any) -> list[str]:
        if items is None:
            return []
        result = []
        for item in items:
            if isinstance(item, bytes):
                result.append(item.decode("utf-8", errors="replace"))
            elif isinstance(item, str):
                result.append(item)
            else:
                result.append(str(item))
        return result

    def _row_to_record(self, row: dict[str, Any], columns: list[str] | None = None) -> Any:
        from app.memory.memory import MemoryRecord

        def _parse_dt(val: Any) -> datetime:
            if val is None:
                return datetime.utcnow()
            if isinstance(val, datetime):
                return val
            return datetime.fromisoformat(str(val).replace("Z", "+00:00"))

        def _parse_metadata(val: Any) -> dict:
            if val is None:
                return {}
            if isinstance(val, dict):
                return val
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, ValueError):
                    return {}
            return {}

        record_data = {
            "id": str(row.get("id", "")),
            "content": str(row.get("content", "")),
            "scope": str(row.get("scope", "/")),
            "metadata": _parse_metadata(row.get("metadata")),
            "images": self._from_bytes_list(row.get("images")),
            "audio": self._from_bytes_list(row.get("audio")),
            "videos": self._from_bytes_list(row.get("videos")),
            "created_at": _parse_dt(row.get("created_at")),
            "embedding": row.get("vector"),
        }

        if columns:
            all_fields = {"content", "scope", "metadata", "images", "audio", "videos", "created_at"}
            exclude = all_fields - set(columns)
            for field in exclude:
                if field == "content":
                    record_data["content"] = ""
                elif field == "metadata":
                    record_data["metadata"] = {}
                elif field in ("images", "audio", "videos"):
                    record_data[field] = []

        return MemoryRecord(**record_data)

    def save_embedded(self, records: list, table_name: str | None = None) -> None:
        if not records:
            return
        dim = next((len(r.embedding) for r in records if r.embedding), None)
        if table_name == CONVERSATIONS_TABLE_NAME:
            self._ensure_conversations_table(vector_dim=dim)
            target_table = self._conversations_table
        else:
            self._ensure_table(vector_dim=dim)
            target_table = self._table
        rows = [self._record_to_row(rec) for rec in records]
        for row in rows:
            if row["vector"] is None or len(row["vector"]) != self._vector_dim:
                row["vector"] = [0.0] * self._vector_dim
        target_table.add(rows)

    def search(
        self,
        query_embedding: list[float],
        query_text: str = "",
        scope_prefixes: list[str] | None = None,
        filters: str | None = None,
        limit: int = 10,
        columns: list[str] | None = None,
        table_name: str | None = None,
    ) -> list[tuple[Any, float]]:
        target_table = self.get_table(table_name)
        if target_table is None:
            return []

        query = target_table.search(query_embedding)

        scope_expr = None
        if scope_prefixes:
            valid = [s.rstrip("/") for s in scope_prefixes if s and s.strip("/")]
            if len(valid) == 1:
                scope_expr = f"scope LIKE '{valid[0]}%'"
            elif len(valid) > 1:
                parts = [f"scope LIKE '{p}%'" for p in valid]
                scope_expr = "(" + " OR ".join(parts) + ")"

        if scope_expr and filters:
            combined = f"({scope_expr}) AND ({filters})"
            query = query.where(combined, prefilter=True)
        elif scope_expr:
            query = query.where(scope_expr, prefilter=True)
        elif filters:
            query = query.where(filters, prefilter=True)

        fetch_limit = limit * 2
        results = query.limit(fetch_limit).to_list()

        out: list[tuple[Any, float]] = []
        for row in results:
            record = self._row_to_record(row, columns=columns)
            out.append((record, row.get("_relevance_score", row.get("_distance", 0.0))))
            if len(out) >= limit:
                break
        return out[:limit]

    def delete(self, scope_prefix: str | None = None, scope_prefixes: list[str] | None = None, record_ids: list[str] | None = None) -> int:
        if self._table is None:
            return 0
        if record_ids:
            before = int(self._table.count_rows())
            ids_expr = ", ".join(f"'{rid}'" for rid in record_ids)
            self._table.delete(f"id IN ({ids_expr})")
            return before - int(self._table.count_rows())

        prefixes = scope_prefixes or ([scope_prefix] if scope_prefix else [])
        if prefixes:
            valid = [p.rstrip("/") for p in prefixes if p and p.strip("/")]
            if not valid:
                return 0
            before = int(self._table.count_rows())
            if len(valid) == 1:
                self._table.delete(f"scope LIKE '{valid[0]}%'")
            else:
                parts = " OR ".join(f"scope LIKE '{p}%'" for p in valid)
                self._table.delete(f"({parts})")
            return before - int(self._table.count_rows())

        before = int(self._table.count_rows())
        self._table.delete("id != ''")
        return before

    def delete_by_id(self, record_id: str) -> None:
        if self._table is None:
            return
        self._table.delete(f"id = '{record_id}'")

    def fetch(
        self,
        scope_prefixes: list[str] | None = None,
        filters: str | None = None,
        limit: int = 10,
        table_name: str | None = None,
    ) -> list[Any]:

        target_table = self.get_table(table_name)
        if target_table is None:
            return []

        try:
            # Build scope filter
            scope_expr = None
            if scope_prefixes:
                valid = [s.rstrip("/") for s in scope_prefixes if s and s.strip("/")]
                if len(valid) == 1:
                    scope_expr = f"scope LIKE '{valid[0]}%'"
                elif len(valid) > 1:
                    parts = [f"scope LIKE '{p}%'" for p in valid]
                    scope_expr = "(" + " OR ".join(parts) + ")"

     
            combined_filter = None
            if scope_expr and filters:
                combined_filter = f"({scope_expr}) AND ({filters})"
            elif scope_expr:
                combined_filter = scope_expr
            elif filters:
                combined_filter = filters

        
            if combined_filter:
                df = target_table.to_pandas()
                # Apply filter manually using pandas
                if scope_prefixes:
                    valid = [s.rstrip("/") for s in scope_prefixes if s and s.strip("/")]
                    mask = None
                    for prefix in valid:
                        cond = df["scope"].str.startswith(prefix)
                        mask = cond if mask is None else (mask | cond)
                    if mask is not None:
                        df = df[mask]
            else:
                df = target_table.to_pandas()

            if df.empty:
                return []

            records = []
            for _, row in df.iterrows():
                record = self._row_to_record(row.to_dict())
                records.append(record)

            # Sort ascending by time, then take the LAST N (most recent) messages
            records.sort(key=lambda r: r.created_at)
            return records[-limit:]

        except Exception as e:
            logger.warning("fetch failed: %s", e)
            return []

    def save(self, records: list, table_name: str | None = None) -> None:
   
        if not records:
            return

        if table_name == CONVERSATIONS_TABLE_NAME:
            self._ensure_conversations_table()
            target_table = self._conversations_table
        else:
            self._ensure_table()
            target_table = self._table

        if target_table is None:
            return

        rows = [self._record_to_row(rec) for rec in records]
        for row in rows:
           
            row["vector"] = [0.0] * self._vector_dim
        target_table.add(rows)

    def count(self, scope_prefix: str | None = None) -> int:
        if self._table is None:
            return 0
        return int(self._table.count_rows())
