import ast
import json
import logging
import os
import time
from concurrent.futures import Future
from pathlib import Path
from typing import Any

import requests
from langchain_core.documents import Document
from langchain_core.runnables import RunnableAssign, RunnableLambda
from langchain_core.vectorstores import VectorStore
from nvidia_rag.utils.embedding import get_embedding_model
from nvidia_rag.rag_server.response_generator import APIError, ErrorCodeMapping
from nvidia_rag.utils.common import (
    get_current_timestamp,
    perform_document_info_aggregation,

)

from nvidia_rag.utils.configuration import NvidiaRAGConfig
from nvidia_rag.utils.health_models import ServiceStatus
from nvidia_rag.utils.vdb import (
    DEFAULT_DOCUMENT_INFO_COLLECTION,
    DEFAULT_METADATA_SCHEMA_COLLECTION,
    SYSTEM_COLLECTIONS,
)
from nvidia_rag.utils.vdb.vdb_ingest_base import VDBRagIngest


from langchain_community.vectorstores import LanceDB
from langchain_core.documents import Document


class NRLLanceDB(LanceDB):

    @staticmethod
    def _parse_metadata(metadata: Any) -> dict[str, Any]:
        if metadata is None:
            return {}

        if isinstance(metadata, dict):
            return metadata

        if isinstance(metadata, str):
            try:
                parsed = json.loads(metadata)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass

            try:
                parsed = ast.literal_eval(metadata)
                if isinstance(parsed, dict):
                    return parsed
            except (ValueError, SyntaxError):
                pass

        return {"metadata": metadata}

    @staticmethod
    def _rows_from_results(results: Any) -> list[dict[str, Any]]:
        if results is None:
            return []

        if hasattr(results, "to_pylist"):
            return results.to_pylist()

        if hasattr(results, "to_dict"):
            try:
                rows = results.to_dict(orient="records")
                if isinstance(rows, list):
                    return rows
            except TypeError:
                pass

        if isinstance(results, list):
            return [
                row
                for row in results
                if isinstance(row, dict)
            ]

        if isinstance(results, dict):
            values = list(results.values())

            if not values:
                return []

            if not any(isinstance(v, (list, tuple)) for v in values):
                return [dict(results)]

            keys = list(results.keys())

            return [
                {
                    key: results[key][index]
                    for key in keys
                }
                for index in range(len(values[0]))
            ]

        return []

    @staticmethod
    def _is_large_string(value: Any) -> bool:
        return isinstance(value, str) and len(value) > 100000

    @classmethod
    def _sanitize_source(cls, source: Any) -> dict[str, Any]:
        if not isinstance(source, dict):
            source = {}

        source = dict(source)

        description = source.get("description")

        if cls._is_large_string(description):
            source["description"] = "Image content"

        return source

    def results_to_docs(
        self,
        results: Any,
        score: bool = False,
    ) -> list[Document]:

        rows = self._rows_from_results(results)

        docs: list[Document] = []

        for row in rows:
            row_data = dict(row)

            text_key = getattr(self, "_text_key", "text")

            text = row_data.pop(
                text_key,
                row_data.pop("text", ""),
            )

            raw_metadata = row_data.pop("metadata", None)

            metadata = self._parse_metadata(raw_metadata)

            source = metadata.get("source")

            if isinstance(source, dict):
                source = self._sanitize_source(source)
            else:
                source = {}

            for key, value in row_data.items():
                if key not in metadata:
                    metadata[key] = value

            source_id = row.get("source_id")

            if source_id is not None:
                source["source_id"] = str(source_id)

            path = row.get("path")

            if path is not None:
                source["path"] = str(path)

            document_id = row.get("document_id")

            if document_id is not None:
                metadata["document_id"] = str(document_id)

            document_name = row.get("document_name")

            if document_name is not None:
                metadata["document_name"] = str(document_name)

            row_id = row.get("id")

            if row_id is not None:
                metadata["id"] = str(row_id)

            metadata["source"] = source

            if score:
                distance = row.get("_distance")

                if distance is not None:
                    metadata["_score"] = distance

            docs.append(
                Document(
                    page_content=str(text or ""),
                    metadata=metadata,
                )
            )

        return docs


logger = logging.getLogger(__name__)

_LANCEDB_INSTALL_MSG = (
    "lancedb is required for LanceDBVDB. "
    "Install with: uv sync --extra rag (includes lancedb), "
    "pip install 'nvidia-rag[lancedb]', or pip install 'lancedb>=0.26,<0.30'."
)


def release_nvidia_client_response(response: Any) -> None:
    """
    Safely releases and cleans up the client response object context memory,
    preventing leaks during active distributed async stream ingest cycles.
    """
    if response is None:
        return
    try:
        # Standard response/client objects may expose close().
        close = getattr(response, "close", None)
        if callable(close):
            close()

        # Some dataframe/collection-like response containers expose clear().
        clear = getattr(response, "clear", None)
        if callable(clear):
            clear()
    except Exception as exc:
        logger.debug(
            "Non-fatal error in custom response release: %s",
            exc,
            exc_info=True,
        )


def _import_lancedb():
    """Import lancedb, raising a clear error if the package is missing."""
    try:
        import lancedb as lancedb_mod

        return lancedb_mod
    except ImportError as exc:
        raise ImportError(_LANCEDB_INSTALL_MSG) from exc


def _parse_nrl_metadata(val: Any) -> dict:
    """Parse NRL's ``str(dict)`` metadata representation to a Python dict.

    NRL stores the metadata field as ``str(meta)`` — a Python repr string using
    single quotes and Python boolean literals (``True``/``False``/``None``).
    Returns an empty dict for null or unparseable values instead of raising.
    """
    if not val:
        return {}
    if isinstance(val, dict):
        return val
    try:
        parsed = ast.literal_eval(str(val))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        logger.debug("_parse_nrl_metadata: could not parse value: %r", val)
        return {}


def _json_safe(value: Any) -> Any:
    """Return a JSON-serialisable representation of a metadata value."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    try:
        import numpy as np
        if isinstance(value, np.ndarray):
            return [_json_safe(v) for v in value.tolist()]
        if isinstance(value, np.generic):
            return value.item()
    except Exception:
        pass
    return str(value)


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _coerce_embedding(value: Any) -> list[float] | None:
    """Convert a possible embedding payload into a flat float vector.

    NV-Ingest/NRL has used several representations across releases:
    - list[float]
    - numpy arrays
    - {"embedding": list[float]}
    - {"vector": list[float]}
    - list[{"embedding": list[float]}]
    - nested one-row arrays such as [[...]]
    """
    if value is None:
        return None

    if hasattr(value, "tolist"):
        try:
            value = value.tolist()
        except Exception:
            pass

    if isinstance(value, dict):
        for key in (
            "embedding",
            "vector",
            "embeddings",
            "text_embeddings_1b_v2",
            "output",
            "outputs",
            "data",
        ):
            if key in value:
                result = _coerce_embedding(value[key])
                if result is not None:
                    return result
        return None

    if isinstance(value, (list, tuple)):
        if not value:
            return None

        # Direct vector: every element must be numeric.
        try:
            return [float(x) for x in value]
        except (TypeError, ValueError):
            pass

        # Batch/nested representation. Pick the first valid embedding.
        for item in value:
            result = _coerce_embedding(item)
            if result is not None:
                return result

    return None


def _extract_embedding(record: dict[str, Any]) -> list[float] | None:
    """Extract the document embedding from NV-Ingest/NRL result records.

    The embedding task configured by NVIDIA RAG writes its result to the
    ``text_embeddings_1b_v2`` output column. Depending on the installed
    NV-Ingest/NeMo Retriever version, that column can be represented as a
    vector, a one-row nested vector, a dict, or a list of result objects.
    We therefore search the known embedding fields recursively instead of
    assuming one exact record shape.
    """
    embedding_keys = (
        "vector",
        "embedding",
        "embeddings",
        "text_embeddings_1b_v2",
        "text_embedding",
        "embedding_vector",
        "document_embedding",
        "dense_embedding",
    )

    # Prefer canonical embedding fields at the current record level.
    for key in embedding_keys:
        if key in record:
            vector = _coerce_embedding(record.get(key))
            if vector is not None:
                return vector

    # Search known nested containers. This covers NRL metadata/content wrappers.
    for parent_key in ("content", "content_metadata", "metadata", "result", "data"):
        parent = record.get(parent_key)
        if isinstance(parent, dict):
            for key in embedding_keys:
                if key in parent:
                    vector = _coerce_embedding(parent.get(key))
                    if vector is not None:
                        return vector

    # Last-resort recursive search for embedding-named keys. This handles
    # future NV-Ingest wrappers without treating arbitrary numeric metadata as
    # an embedding.
    def walk(value: Any, depth: int = 0) -> list[float] | None:
        if depth > 6:
            return None

        if isinstance(value, dict):
            for key, child in value.items():
                key_str = str(key).lower()
                if any(token in key_str for token in (
                    "embedding",
                    "embeddings",
                    "text_embeddings",
                    "vector",
                )):
                    vector = _coerce_embedding(child)
                    if vector is not None:
                        return vector
                vector = walk(child, depth + 1)
                if vector is not None:
                    return vector

        elif isinstance(value, (list, tuple)):
            for child in value:
                # Do not walk arbitrary numeric vectors here; those were
                # handled by _coerce_embedding above.
                if isinstance(child, (dict, list, tuple)):
                    vector = walk(child, depth + 1)
                    if vector is not None:
                        return vector

        return None

    return walk(record)


def _extract_record_metadata(record: dict[str, Any]) -> dict[str, Any]:
    """Build the serialized metadata field expected by the RAG blueprint."""
    raw = record.get("metadata")

    if isinstance(raw, dict):
        metadata = dict(raw)
    elif raw:
        metadata = _parse_nrl_metadata(raw)
    else:
        metadata = {}

    # Preserve useful top-level content metadata without duplicating core columns.
    for key in (
        "page_number",
        "page_num",
        "page",
        "content_type",
        "source_name",
        "source_id",
        "source_location",
        "source_type",
        "collection_id",
        "pdf_basename",
        "pdf_page",
    ):
        if key in record and key not in metadata and record[key] is not None:
            metadata[key] = _json_safe(record[key])

    for key in ("content_metadata",):
        value = record.get(key)
        if isinstance(value, dict):
            for k, v in value.items():
                metadata.setdefault(k, _json_safe(v))

    # Embeddings should never be duplicated inside the metadata string.
    for key in ("embedding", "vector", "text_embeddings_1b_v2"):
        metadata.pop(key, None)

    return metadata


def _extract_text(record: dict[str, Any]) -> str:
    for key in ("text", "content", "page_content", "text_content"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value

    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        for key in ("text", "content", "page_content", "text_content"):
            value = metadata.get(key)
            if isinstance(value, str) and value:
                return value

    return ""


def _extract_source_id(record: dict[str, Any], metadata: dict[str, Any]) -> str:
    value = _first_non_empty(
        record.get("source_id"),
        record.get("source_name"),
        record.get("source"),
        metadata.get("source_id"),
        metadata.get("source_name"),
        record.get("path"),
    )
    return str(value) if value is not None else ""


def _extract_path(record: dict[str, Any], metadata: dict[str, Any]) -> str:
    value = _first_non_empty(
        record.get("path"),
        record.get("source_location"),
        metadata.get("source_location"),
        record.get("source_id"),
        record.get("source_name"),
    )
    return str(value) if value is not None else ""


def _normalize_vdb_records(records: Any) -> list[dict[str, Any]]:
    """Normalize the different record containers emitted by NV-Ingest/NRL.

    In the current NVIDIA RAG/NV-Ingest combination the VDB callback can
    receive a list whose item is itself a list of row dictionaries, e.g.::

        [[{"text": "...", "text_embeddings_1b_v2": [...]}]]

    Treating that inner list as a record causes embedding extraction to fail.
    Flatten only container levels and never flatten values inside a row dict.
    """
    if records is None:
        return []

    # pandas DataFrame / compatible objects
    if hasattr(records, "to_dict") and not isinstance(records, (list, tuple, dict)):
        try:
            records = records.to_dict("records")
        except Exception as exc:
            raise TypeError(
                f"Unable to convert NV-Ingest records to row dictionaries: {exc}"
            ) from exc

    if isinstance(records, dict):
        return [records]

    if not isinstance(records, (list, tuple)):
        logger.warning(
            "_normalize_vdb_records: unsupported records type: %s",
            type(records).__name__,
        )
        return []

    normalized: list[dict[str, Any]] = []

    def flatten(value: Any, depth: int = 0) -> None:
        if depth > 10:
            logger.warning(
                "_normalize_vdb_records: maximum nesting depth reached.")
            return

        if isinstance(value, dict):
            normalized.append(value)
            return

        if isinstance(value, (list, tuple)):
            for item in value:
                flatten(item, depth + 1)
            return

        # Ignore scalar wrappers; they cannot represent a VDB row.
        logger.debug(
            "_normalize_vdb_records: ignoring scalar item of type %s",
            type(value).__name__,
        )

    flatten(records)
    return normalized


def _describe_record_shapes(records: Any, limit: int = 3) -> list[dict[str, Any]]:
    """Return safe diagnostics for records that failed embedding extraction."""
    descriptions: list[dict[str, Any]] = []

    try:
        iterable = _normalize_vdb_records(records)
    except Exception:
        iterable = records

    if not isinstance(iterable, (list, tuple)):
        return [{"type": type(iterable).__name__}]

    for record in list(iterable)[:limit]:
        if not isinstance(record, dict):
            descriptions.append({"type": type(record).__name__})
            continue

        descriptions.append({
            "type": type(record).__name__,
            "keys": list(record.keys()),
            "embedding_keys": [
                str(k) for k in record.keys()
                if any(token in str(k).lower() for token in ("embedding", "vector"))
            ],
            "types": {
                str(k): type(v).__name__
                for k, v in record.items()
                if any(token in str(k).lower() for token in ("embedding", "vector"))
            },
        })

    return descriptions


def _build_rows_with_embedding_fallback(
    records: list[dict[str, Any]],
    embedding_model: Any,
    vector_dim: int | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Build LanceDB rows, generating missing document vectors when necessary.

    NV-Ingest normally supplies ``text_embeddings_1b_v2``. Some combinations of
    NVIDIA RAG/NV-Ingest can return a successful extraction result without that
    field being materialized in the raw records passed to the custom VDB. In
    that case we use the exact same configured NVIDIA embedding client used for
    retrieval to embed the extracted text. This keeps ingestion and retrieval in
    the same 2048-dimensional vector space and avoids dropping the document.
    """
    rows, inferred_dim = _build_lancedb_rows(records, vector_dim=vector_dim)
    if rows:
        return rows, inferred_dim

    if embedding_model is None:
        return rows, inferred_dim

    text_records: list[tuple[dict[str, Any], str]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        text = _extract_text(record)
        if text.strip():
            text_records.append((record, text))

    if not text_records:
        return rows, inferred_dim

    texts = [text for _, text in text_records]
    logger.warning(
        "No document embeddings were materialized by NV-Ingest. "
        "Generating %d document embedding(s) with the configured NVIDIA embedding client.",
        len(texts),
    )

    try:
        vectors = embedding_model.embed_documents(texts)
    except Exception:
        logger.exception("Document embedding fallback failed.")
        return rows, inferred_dim

    if not vectors:
        return rows, inferred_dim

    fallback_records: list[dict[str, Any]] = []
    for (record, _), vector in zip(text_records, vectors):
        copied = dict(record)
        copied["vector"] = vector
        fallback_records.append(copied)

    return _build_lancedb_rows(fallback_records, vector_dim=vector_dim)


def _build_lancedb_rows(
    records: list[dict[str, Any]],
    vector_dim: int | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Convert NV-Ingest/NVIDIA RAG records into current LanceDB rows.

    This replaces the removed ``nemo_retriever.vector_store`` helpers from
    pre-26.5 NeMo Retriever releases.
    """
    rows: list[dict[str, Any]] = []
    inferred_dim = vector_dim

    for record in records:
        if not isinstance(record, dict):
            continue

        vector = _extract_embedding(record)
        if vector is None:
            logger.debug("Skipping record without an embedding.")
            continue

        if inferred_dim is None:
            inferred_dim = len(vector)

        if len(vector) != inferred_dim:
            logger.warning(
                "Skipping record with embedding dimension %d; expected %d.",
                len(vector),
                inferred_dim,
            )
            continue

        metadata = _extract_record_metadata(record)
        text = _extract_text(record)
        source_id = _extract_source_id(record, metadata)
        path = _extract_path(record, metadata)

        # NVIDIA RAG document identity is stored as real LanceDB columns.
        # Keep these values OUT of the serialized metadata column.  The
        # post-ingestion validation in NVIDIA RAG expects to be able to find
        # document identity directly in the vector table.

        source_meta = metadata.get(
            "source_metadata", {}) if isinstance(metadata, dict) else {}
        if not isinstance(source_meta, dict):
            source_meta = {}

        document_id = _first_non_empty(
            record.get("document_id"),
            record.get("doc_id"),
            metadata.get("document_id"),
            metadata.get("doc_id"),
            source_meta.get("document_id"),
            source_meta.get("doc_id"),
            record.get("id"),
            source_id,
            path,
        ) or ""

        document_name = _first_non_empty(
            record.get("document_name"),
            record.get("filename"),
            record.get("file_name"),
            record.get("source_name"),
            metadata.get("document_name"),
            metadata.get("filename"),
            metadata.get("file_name"),
            source_meta.get("document_name"),
            source_meta.get("filename"),
            path,
        ) or "unknown_document"

        # id is the chunk/row identifier. Prefer an upstream id; otherwise
        # generate a deterministic identifier so re-reading the same chunk
        # does not randomly change its identity.
        row_id = _first_non_empty(
            record.get("id"),
            record.get("chunk_id"),
            metadata.get("chunk_id"),
            source_meta.get("chunk_id"),
        )
        if not row_id:
            import hashlib
            row_key = f"{document_id}|{document_name}|{path}|{text}"
            row_id = hashlib.sha256(row_key.encode("utf-8")).hexdigest()

        rows.append(
            {
                "id": str(row_id),
                "document_id": str(document_id),
                "document_name": str(document_name),
                "vector": vector,
                "text": text,
                "source_id": str(source_id),
                "path": str(path),
                "metadata": json.dumps(
                    metadata,
                    ensure_ascii=False,
                    default=str,
                ),
            }
        )

    if inferred_dim is None:
        inferred_dim = 0

    return rows, inferred_dim


def _lancedb_schema(vector_dim: int):
    """Create the stable LanceDB schema used by the RAG blueprint."""
    import pyarrow as pa

    if vector_dim <= 0:
        raise ValueError(f"Embedding dimension must be > 0, got {vector_dim}")

    return pa.schema(
        [
            pa.field("id", pa.string()),
            pa.field("document_id", pa.string()),
            pa.field("document_name", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), vector_dim)),
            pa.field("text", pa.string()),
            pa.field("source_id", pa.string()),
            pa.field("path", pa.string()),
            pa.field("metadata", pa.string()),
        ]
    )


def _create_lancedb_index(table: Any, *, hybrid: bool = False) -> None:
    """Create useful LanceDB indexes when the table has enough rows.

    Dense search works without an ANN index, so index creation is deliberately
    best-effort. This is important for small development/test collections.
    """
    try:
        row_count = table.count_rows()
    except Exception:
        row_count = 0

    if row_count >= 16:
        try:
            table.create_index(
                vector_column_name="vector",
                index_type="IVF_HNSW_SQ",
                num_partitions=min(16, max(1, row_count // 2)),
                replace=True,
            )
            logger.info("Created LanceDB IVF_HNSW_SQ index.")
        except Exception as exc:
            logger.warning(
                "Could not create vector index; brute-force search remains available: %s", exc)
    else:
        logger.debug(
            "Skipping ANN index because table contains only %d rows; "
            "LanceDB can still perform brute-force vector search.",
            row_count,
        )

    if hybrid:
        try:
            table.create_fts_index("text", replace=True)
            logger.info("Created LanceDB FTS index.")
        except Exception as exc:
            logger.warning("Could not create LanceDB FTS index: %s", exc)


class VectorDB(VDBRagIngest):
    """
    Parameters
    ----------
    table_name:
        LanceDB table name (equivalent to collection_name in other backends).
    uri:
        Path to the LanceDB database directory, e.g. ``"/data/lancedb"``
        or a cloud URI supported by LanceDB.
    embedding_model:
        LangChain-compatible embedding model for retrieval queries.
    config:
        NvidiaRAGConfig instance. Defaults to a new NvidiaRAGConfig().
    hybrid:
        When True, also create a full-text search (FTS) index for hybrid
        dense+sparse retrieval.
    overwrite:
        When False (default), each ``write_to_index`` call appends to the
        existing table so previously ingested documents are preserved.
        Set to True only when a full table replacement is explicitly desired.
    """

    def __init__(
        self,
        namespace: str,
        table_name: str,
        uri: str = "./data",
        embedding_model: Any = None,
        config: NvidiaRAGConfig | None = None,
        hybrid: bool = False,
        overwrite: bool = False,
    ) -> None:
        self.config = config
        self._table_name = table_name
        self.uri = Path(uri) / namespace
        # Reuse the embedding model supplied by the caller when available.
        # Otherwise create exactly one NVIDIA embedding client from the same
        # configuration used by NvidiaRAG/NvidiaRAGIngestor.
        if embedding_model is not None:
            self.embedding_model = embedding_model
        else:
            self.embedding_model = get_embedding_model(
                model=self.config.embeddings.model_name,
                url=self.config.embeddings.server_url or "",
                config=self.config,
            )

        self._embedding_model = self.embedding_model
        self.hybrid = hybrid
        self.overwrite = overwrite

        # Track if system collections have been initialized (avoid repeated create calls)
        self._metadata_schema_collection_initialized = False
        self._document_info_collection_initialized = False

    @property
    def collection_name(self) -> str:
        """Get the table name"""
        return self._table_name

    @collection_name.setter
    def collection_name(self, collection_name: str) -> None:
        """Set the active LanceDB table/collection name."""
        if not collection_name or not str(collection_name).strip():
            raise ValueError("collection_name must not be empty")
        self._table_name = str(collection_name).strip()

    def set_collection(self, collection_name: str) -> None:
        """Set the active collection used by NVIDIA RAG ingestion.

        When ``NvidiaRAGIngestor`` is constructed with ``vdb_op=self``,
        NVIDIA RAG 2.5.x does not allow ``collection_name`` to be passed to
        ``create_collection`` or ``upload_documents``.  The custom VDB
        therefore needs an explicit active collection that NVIDIA RAG can
        resolve through the VDB instance itself.
        """
        self.collection_name = collection_name

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def check_health(self) -> dict[str, Any]:
        """Check LanceDB health by attempting to connect and list tables."""
        status: dict[str, Any] = {
            "service": "LanceDB",
            "url": self.uri,
            "status": ServiceStatus.UNKNOWN.value,
            "error": None,
        }
        if not self.uri:
            status["status"] = ServiceStatus.SKIPPED.value
            status["error"] = "No URI provided"
            return status
        try:
            lancedb_mod = _import_lancedb()

            db = lancedb_mod.connect(self.uri)
            tables = db.table_names()
            status["status"] = ServiceStatus.HEALTHY.value
            status["tables"] = len(tables)
        except Exception as exc:
            status["status"] = ServiceStatus.ERROR.value
            status["error"] = str(exc)
        return status

    # ------------------------------------------------------------------
    # NV-Ingest Client VDB interface
    # ------------------------------------------------------------------

    def create_index(self, **kwargs) -> None:
        """Ensure the LanceDB table exists with the current NRL-compatible schema."""
        lancedb_mod = _import_lancedb()
        import pyarrow as pa  # noqa: PLC0415

        self.uri.mkdir(parents=True, exist_ok=True)
        db = lancedb_mod.connect(self.uri)

        try:
            table = db.open_table(self._table_name)
            existing_fields = {field.name for field in table.schema}
            required_fields = {
                "id",
                "document_id",
                "document_name",
                "vector",
                "text",
                "source_id",
                "path",
                "metadata",
            }

            missing_fields = required_fields - existing_fields
            if missing_fields:
                # Migrate an existing table created by the previous five-column
                # implementation. LanceDB supports adding nullable columns to
                # an existing table. New writes will populate all three identity
                # columns; old rows are retained.
                try:
                    additions: dict[str, str] = {}
                    if "id" in missing_fields:
                        additions["id"] = "cast('' as string)"
                    if "document_id" in missing_fields:
                        additions["document_id"] = "cast('' as string)"
                    if "document_name" in missing_fields:
                        additions["document_name"] = "cast('' as string)"

                    if additions:
                        table.add_columns(additions)
                        table = db.open_table(self._table_name)
                        existing_fields = {
                            field.name for field in table.schema}
                except Exception as exc:
                    raise RuntimeError(
                        f"LanceDB table '{self._table_name}' requires migration to add "
                        f"{sorted(missing_fields)}, but migration failed: {exc}. "
                        f"Existing fields: {sorted(existing_fields)}."
                    ) from exc

            missing_after_migration = required_fields - existing_fields
            if missing_after_migration:
                raise RuntimeError(
                    f"LanceDB table '{self._table_name}' has an incompatible schema. "
                    f"Missing required fields: {sorted(missing_after_migration)}. "
                    f"Existing fields: {sorted(existing_fields)}."
                )

            logger.info(
                "LanceDB table '%s' is ready with fields %s.",
                self._table_name,
                [field.name for field in table.schema],
            )
            return
        except RuntimeError:
            raise
        except Exception:
            pass

        dim = int(
            getattr(getattr(self.config, "embeddings", None), "dimensions", 0)
            or 0
        )
        if dim <= 0:
            dim = 2048

        schema = _lancedb_schema(dim)
        empty = pa.table(
            {field.name: pa.array([], type=field.type) for field in schema},
            schema=schema,
        )
        db.create_table(
            self._table_name,
            data=empty,
            schema=schema,
            mode="create",
        )
        logger.info(
            "Created LanceDB table '%s' at '%s' (dim=%d).",
            self._table_name,
            self.uri,
            dim,
        )

    def write_to_index(self, records: list, **kwargs) -> None:
        """Append NV-Ingest/NVIDIA RAG records to the LanceDB table.

        NeMo Retriever 26.5 removed the old ``nemo_retriever.vector_store``
        helper modules.  We therefore use the public LanceDB client directly
        and normalize the records at this boundary.
        """
        # NV-Ingest/NRL can wrap rows in one or more list containers. Normalize
        # that boundary before embedding/text extraction. This is important for
        # the current stack where the callback may arrive as [[row_dict]].
        raw_record_count = len(records) if hasattr(records, "__len__") else 1
        records = _normalize_vdb_records(records)

        logger.debug(
            "write_to_index: normalized %d raw container item(s) to %d row(s).",
            raw_record_count,
            len(records),
        )

        if not records:
            logger.warning(
                "write_to_index: no records provided for LanceDB table '%s'; skipping.",
                self._table_name,
            )
            return

        lancedb_mod = _import_lancedb()
        self.uri.mkdir(parents=True, exist_ok=True)
        db = lancedb_mod.connect(self.uri)

        rows, inferred_dim = _build_rows_with_embedding_fallback(
            records,
            embedding_model=self.embedding_model,
            vector_dim=(
                int(
                    getattr(
                        getattr(self.config, "embeddings", None),
                        "dimensions",
                        0,
                    )
                    or 0
                )
                or None
            ),
        )

        if not rows:
            logger.warning(
                "write_to_index: no records containing valid embeddings were found; skipping."
            )
            logger.warning(
                "write_to_index: received %d record(s); raw record shapes: %s",
                len(records),
                _describe_record_shapes(records),
            )
            return

        # If the table was created with a different configured dimension, use
        # the actual record dimension for a new table.
        if self._table_name not in db.table_names():
            import pyarrow as pa  # noqa: PLC0415

            schema = _lancedb_schema(inferred_dim)
            empty = pa.table(
                {field.name: pa.array([], type=field.type)
                 for field in schema},
                schema=schema,
            )
            db.create_table(
                self._table_name,
                data=empty,
                schema=schema,
                mode="create",
            )

        table = db.open_table(self._table_name)

        # Validate against the existing table's vector dimension.
        try:
            vector_field = next(
                field for field in table.schema if field.name == "vector"
            )
            existing_dim = vector_field.type.list_size
            if existing_dim > 0 and existing_dim != inferred_dim:
                raise ValueError(
                    f"LanceDB table '{self._table_name}' expects embedding dimension "
                    f"{existing_dim}, but received {inferred_dim}."
                )
        except StopIteration:
            raise RuntimeError(
                f"LanceDB table '{self._table_name}' does not contain a vector column."
            )

        # LanceDB requires the incoming row schema to be compatible with the
        # existing table schema. Keep this explicit so a stale/custom table
        # cannot fail later with an opaque "Field ... not found" exception.
        target_fields = [field.name for field in table.schema]
        row_fields = set(rows[0].keys())

        unexpected_fields = row_fields - set(target_fields)
        missing_fields = set(target_fields) - row_fields

        if unexpected_fields:
            raise RuntimeError(
                f"LanceDB table '{self._table_name}' rejects incoming fields "
                f"{sorted(unexpected_fields)}. Target schema: {target_fields}. "
                "The VDB row builder must only emit fields declared by the table."
            )

        if missing_fields:
            raise RuntimeError(
                f"LanceDB table '{self._table_name}' requires fields "
                f"{sorted(missing_fields)}, but the VDB row builder produced "
                f"{sorted(row_fields)}. Target schema: {target_fields}."
            )

        # Reorder the dictionaries to exactly match the Arrow/LanceDB schema.
        rows = [{field: row[field] for field in target_fields} for row in rows]

        logger.info(
            "Appending %d rows to LanceDB table '%s' with fields %s.",
            len(rows),
            self._table_name,
            target_fields,
        )
        table.add(rows)

        _create_lancedb_index(table, hybrid=self.hybrid)

        logger.info(
            "Appended %d rows to LanceDB table '%s'.",
            len(rows),
            self._table_name,
        )

    def run(self, records: list) -> None:
        """Orchestrate index creation and NRL record ingestion.

        Parameters
        ----------
        records:
            Raw NRL DataFrame records from ``IngestSchemaManager.to_raw_records()``.
        """
        logger.info(
            "LanceDBVDB.run: creating index for table '%s'.", self._table_name)
        self.create_index()
        logger.info(
            "LanceDBVDB.run: writing records to table '%s'.", self._table_name)
        self.write_to_index(records)

    def run_async(self, records: list | Future) -> list:
        """Async-compatible ingestion entry point.

        Parameters
        ----------
        records:
            Raw NRL DataFrame records, or a ``concurrent.futures.Future`` that
            resolves to such records.

        Returns
        -------
        list
            The records that were written (resolved from the Future if needed).
        """
        logger.info(
            "LanceDBVDB.run_async: creating index for table '%s'.", self._table_name)
        self.create_index()

        if isinstance(records, Future):
            records = records.result()

        logger.info(
            "LanceDBVDB.run_async: writing records to table '%s'.", self._table_name)
        self.write_to_index(records)
        return records

    def retrieval(self, queries: list, **kwargs) -> list:
        """VDB ABC stub — use retrieval_langchain for RAG queries."""
        raise NotImplementedError(
            "retrieval() is not implemented for LanceDBVDB. "
            "Use retrieval_langchain() instead."
        )

    def reindex(self, records: list, **kwargs) -> None:
        """Re-ingest records with overwrite semantics."""
        old_overwrite = self.overwrite
        self.overwrite = True
        try:
            self.run(records)
        finally:
            self.overwrite = old_overwrite

    # ------------------------------------------------------------------
    # Collection Management
    # ------------------------------------------------------------------

    def create_collection(
        self,
        collection_name: str,
        dimension: int = 2048,
        collection_type: str = "text",
    ) -> None:
        """Create a LanceDB collection/table using the current schema.

        ``nemo_retriever.vector_store.lancedb_utils`` was removed from the
        NeMo Retriever 26.5 package.  The schema is now kept locally so the
        NVIDIA RAG Blueprint can continue to use its ``create_collection``
        contract without relying on private NeMo Retriever modules.
        """
        del collection_type  # kept for VDBRagIngest compatibility

        # NVIDIA RAG 2.5.x uses the injected VDB's active collection when
        # collection_name is not allowed on the ingestor API.  Always update
        # the active collection, even when the table already exists.
        self.collection_name = collection_name

        lancedb_mod = _import_lancedb()
        import pyarrow as pa  # noqa: PLC0415

        if not collection_name:
            raise ValueError("collection_name must not be empty")
        if dimension <= 0:
            raise ValueError(
                f"Embedding dimension must be > 0, got {dimension}")

        Path(self.uri).mkdir(parents=True, exist_ok=True)
        db = lancedb_mod.connect(self.uri)

        if collection_name in db.table_names():
            logger.debug(
                "LanceDB table '%s' already exists; skipping create_collection.",
                collection_name,
            )
            return

        schema = _lancedb_schema(dimension)
        empty = pa.table(
            {field.name: pa.array([], type=field.type) for field in schema},
            schema=schema,
        )
        db.create_table(
            collection_name,
            data=empty,
            schema=schema,
            mode="create",
        )

        logger.info(
            "Created LanceDB table '%s' (dim=%d) at '%s'.",
            collection_name,
            dimension,
            self.uri,
        )

    def check_collection_exists(self, collection_name: str) -> bool:
        """Return True if the LanceDB table exists."""
        lancedb_mod = _import_lancedb()

        db = lancedb_mod.connect(self.uri)
        return collection_name in db.table_names()

    def get_collection(self) -> list[dict[str, Any]]:
        """Return metadata for all user-facing LanceDB tables.

        Queries the ``metadata_schema`` and ``document_info`` system tables to
        populate ``metadata_schema`` and ``collection_info`` for each table,
        mirroring the behaviour of MilvusVDB / ElasticVDB.

        Returns
        -------
        list[dict]
            Each entry has keys: ``collection_name``, ``num_entities``,
            ``metadata_schema``, ``collection_info``.
        """
        self.create_metadata_schema_collection()
        self.create_document_info_collection()

        lancedb_mod = _import_lancedb()

        db = lancedb_mod.connect(self.uri)
        table_names = db.table_names()
        collections: list[dict[str, Any]] = []
        for name in table_names:
            if name in SYSTEM_COLLECTIONS:
                continue
            try:
                table = db.open_table(name)
                num_rows = table.count_rows()
            except Exception as exc:
                logger.warning(
                    "get_collection: failed to open table '%s': %s", name, exc)
                num_rows = 0

            metadata_schema = self.get_metadata_schema(name)
            catalog_data = self.get_document_info(
                info_type="catalog",
                collection_name=name,
                document_name="NA",
            )
            metrics_data = self.get_document_info(
                info_type="collection",
                collection_name=name,
                document_name="NA",
            )
            collections.append(
                {
                    "collection_name": name,
                    "num_entities": num_rows,
                    "metadata_schema": metadata_schema,
                    "collection_info": {**metrics_data, **catalog_data},
                }
            )
        return collections

    def delete_collections(
        self,
        collection_names: list[str],
    ) -> dict[str, Any]:
        """Drop one or more LanceDB tables and clean up associated metadata.

        Also removes entries from the ``metadata_schema`` and ``document_info``
        system tables for each successfully deleted collection.

        Returns
        -------
        dict
            ``successful`` and ``failed`` lists plus totals.
        """
        lancedb_mod = _import_lancedb()

        db = lancedb_mod.connect(self.uri)
        existing = set(db.table_names())
        deleted: list[str] = []
        failed: list[dict[str, str]] = []

        for name in collection_names:
            try:
                if name in existing:
                    db.drop_table(name)
                    deleted.append(name)
                    logger.info("Deleted LanceDB table '%s'.", name)
                else:
                    failed.append(
                        {
                            "collection_name": name,
                            "error_message": f"Table '{name}' not found.",
                        }
                    )
                    logger.warning(
                        "LanceDB table '%s' not found; skipping deletion.", name)
            except Exception as exc:
                failed.append({"collection_name": name,
                              "error_message": str(exc)})
                logger.error(
                    "Failed to delete LanceDB table '%s': %s", name, exc)

        # Clean up system table entries for successfully deleted collections
        for name in deleted:
            self._delete_from_system_table(
                system_table=DEFAULT_METADATA_SCHEMA_COLLECTION,
                filter_col="collection_name",
                filter_val=name,
            )
            self._delete_from_system_table(
                system_table=DEFAULT_DOCUMENT_INFO_COLLECTION,
                filter_col="collection_name",
                filter_val=name,
            )

        return {
            "message": "Collection deletion process completed.",
            "successful": deleted,
            "failed": failed,
            "total_success": len(deleted),
            "total_failed": len(failed),
        }

    # ------------------------------------------------------------------
    # Document Management
    # ------------------------------------------------------------------

    def get_documents(
        self,
        collection_name: str,
        *,
        force_get_metadata: bool = False,
    ) -> list[dict[str, Any]]:
        """Return documents known to NVIDIA RAG for a LanceDB collection.

        NVIDIA RAG performs post-ingestion validation by comparing the uploaded
        filename with ``document_name`` values returned by this method.

        Important: NV-Ingest's VDB callback does not always include the original
        filename in the records. In that case the vector rows can legitimately
        contain empty/unknown identity fields even though the ingestion layer
        has already registered the document in the ``document_info`` system
        table. Therefore this method treats ``document_info`` as the authoritative
        document catalog and uses vector-row identity as a secondary source.

        The user-facing vector table still stores ``id``, ``document_id`` and
        ``document_name`` as real top-level LanceDB columns.
        """
        lancedb_mod = _import_lancedb()

        metadata_schema = self.get_metadata_schema(collection_name)
        doc_info_map = self._get_document_info_map(collection_name)

        try:
            db = lancedb_mod.connect(self.uri)
            table = db.open_table(collection_name)
            df = table.to_pandas()
        except Exception as exc:
            logger.error(
                "get_documents: failed to open table '%s': %s",
                collection_name,
                exc,
            )
            return []

        documents: list[dict[str, Any]] = []
        seen: set[str] = set()

        def add_document(
            document_name: Any,
            document_id: Any = "",
            metadata: dict[str, Any] | None = None,
            document_info: dict[str, Any] | None = None,
        ) -> None:
            if document_name is None:
                return

            name = str(document_name).strip()
            if not name:
                return

            # Always expose the canonical filename to NVIDIA RAG.  This is
            # intentionally based on basename so paths/URIs cannot break the
            # post-ingestion filename comparison.
            name = os.path.basename(name)

            if not name or name == "unknown_document":
                return

            doc_id = str(document_id or "").strip()
            info = document_info or {}

            # Prefer the document catalog's ID when the VDB row did not have
            # one.  The catalog is created by NVIDIA RAG around the same
            # ingestion operation and is authoritative for document identity.
            if not doc_id:
                doc_id = str(
                    info.get("document_id")
                    or info.get("doc_id")
                    or info.get("id")
                    or ""
                )

            dedupe_key = doc_id or name
            if dedupe_key in seen:
                return
            seen.add(dedupe_key)

            documents.append(
                {
                    "document_id": doc_id,
                    "document_name": name,
                    "metadata": metadata or {},
                    "document_info": info,
                }
            )

        # First read identity from actual vector rows.  Do not let placeholder
        # values such as "unknown_document" become visible to NVIDIA RAG.
        if not df.empty:
            for _, row in df.iterrows():
                raw_name = row.get("document_name")
                raw_path = row.get("path")
                raw_source = row.get("source_id")

                candidate = raw_name or raw_path or raw_source
                if not candidate:
                    continue

                candidate_str = str(candidate).strip()
                if not candidate_str or candidate_str == "unknown_document":
                    continue

                metadata_dict: dict[str, Any] = {}
                if metadata_schema:
                    parsed_meta = _parse_nrl_metadata(row.get("metadata", ""))
                    for schema_item in metadata_schema:
                        field_name = schema_item.get("name")
                        if field_name:
                            metadata_dict[field_name] = parsed_meta.get(
                                field_name)

                doc_name = os.path.basename(candidate_str)
                add_document(
                    doc_name,
                    row.get("document_id"),
                    metadata_dict,
                    doc_info_map.get(doc_name, {}),
                )

        # CRITICAL NVIDIA-RAG COMPATIBILITY:
        # The ingestion server records the uploaded filename in document_info
        # after the VDB write and before it validates get_documents(). If the
        # VDB callback did not carry the filename (the exact situation shown by
        # the identity verification log: unknown_document/empty path), the
        # vector rows alone cannot possibly tell us that the file was
        # "test_v.txt". Use the document catalog to bridge that boundary.
        for doc_name, info in doc_info_map.items():
            add_document(
                doc_name,
                info.get("document_id") if isinstance(info, dict) else "",
                {},
                info if isinstance(info, dict) else {},
            )

        logger.info(
            "get_documents: collection='%s' returned %d document(s): %s",
            collection_name,
            len(documents),
            [d.get("document_name") for d in documents],
        )

        return documents

    def delete_documents(
        self,
        collection_name: str,
        source_values: list[str],
        result_dict: dict[str, list[str]] | None = None,
    ) -> bool:
        """Delete all rows in the table whose ``path`` or ``source_id`` matches.

        Also removes the corresponding ``document`` entries from the
        ``document_info`` system table.

        Parameters
        ----------
        collection_name:
            Target LanceDB table.
        source_values:
            List of source file paths to remove.
        result_dict:
            Optional dict populated with ``"deleted"`` and ``"not_found"`` lists.
        """
        lancedb_mod = _import_lancedb()

        if result_dict is not None:
            result_dict["deleted"] = []
            result_dict["not_found"] = []

        try:
            db = lancedb_mod.connect(self.uri)
            table = db.open_table(collection_name)
        except Exception as exc:
            logger.error(
                "delete_documents: failed to open table '%s': %s",
                collection_name,
                exc,
            )
            return False

        for source_value in source_values:
            doc_name = os.path.basename(source_value)
            escaped = source_value.replace("'", "\\'")
            try:
                count_before = table.count_rows()
                # LanceDB SQL-style predicate: match on either path or source_id column.
                table.delete(f"path = '{escaped}' OR source_id = '{escaped}'")
                count_after = table.count_rows()

                # Also remove document-level info from the document_info system table
                self._delete_document_info_entry(
                    collection_name=collection_name,
                    document_name=doc_name,
                    info_type="document",
                )

                if result_dict is not None:
                    if count_before > count_after:
                        result_dict["deleted"].append(doc_name)
                    else:
                        result_dict["not_found"].append(doc_name)
            except Exception as exc:
                logger.warning(
                    "delete_documents: failed to delete '%s' from '%s': %s",
                    source_value,
                    collection_name,
                    exc,
                )
                if result_dict is not None:
                    result_dict["not_found"].append(doc_name)

        return True

    # ------------------------------------------------------------------
    # Retrieval Operations
    # ------------------------------------------------------------------

    def _hydrate_document_identity(
        self,
        docs: list[Document],
        collection_name: str,
    ) -> list[Document]:
        """Hydrate first-class LanceDB document identity into runtime Documents.

        ``id``, ``document_id`` and ``document_name`` remain physical LanceDB
        columns.  NVIDIA RAG's response/citation layer consumes LangChain
        ``Document.metadata``, so this method copies the already-stored
        top-level values into the transient Document metadata after retrieval.
        Nothing is written back into the LanceDB ``metadata`` column.
        """
        if not docs:
            return docs

        lancedb_mod = _import_lancedb()
        try:
            db = lancedb_mod.connect(self.uri)
            table = db.open_table(collection_name)
            df = table.to_pandas()
        except Exception as exc:
            logger.warning(
                "_hydrate_document_identity: unable to read identity columns "
                "from table '%s': %s",
                collection_name,
                exc,
            )
            return docs

        if df.empty:
            return docs

        # Build fast lookup maps for IDs.  LangChain/NLLanceDB can expose the
        # configured id_key as either ``id`` or ``source_id`` in metadata.
        by_id: dict[str, Any] = {}
        by_source: dict[str, Any] = {}

        for _, row in df.iterrows():
            row_id = row.get("id")
            if row_id is not None and str(row_id):
                by_id[str(row_id)] = row

            source_id = row.get("source_id")
            if source_id is not None and str(source_id):
                by_source[str(source_id)] = row

        for doc in docs:
            if not isinstance(doc.metadata, dict):
                doc.metadata = {}

            candidate_ids = [
                doc.metadata.get("id"),
                doc.metadata.get("document_id"),
                doc.metadata.get("source_id"),
                doc.metadata.get("source"),
            ]

            row = None
            for candidate in candidate_ids:
                if candidate is None:
                    continue
                key = str(candidate)
                row = by_id.get(key)
                if row is None:
                    row = by_source.get(key)
                if row is not None:
                    break

            if row is None:
                # Last-resort content match for NRL/LangChain adapters that
                # don't expose the id_key in Document.metadata.
                content = getattr(doc, "page_content", "")
                if content:
                    matches = df[df["text"].astype(str) == str(content)]
                    if not matches.empty:
                        row = matches.iloc[0]

            if row is None:
                continue

            document_id = row.get("document_id")
            document_name = row.get("document_name")
            row_id = row.get("id")

            if document_id is not None and str(document_id):
                doc.metadata["document_id"] = str(document_id)
            if document_name is not None and str(document_name):
                doc.metadata["document_name"] = str(document_name)
            if row_id is not None and str(row_id):
                doc.metadata["id"] = str(row_id)

        return docs

    def retrieval_langchain(
        self,
        query: str,
        collection_name: str,
        vectorstore: VectorStore | None = None,
        top_k: int = 10,
        filter_expr: str | list[dict[str, Any]] = "",
        otel_ctx: Any | None = None,
    ) -> list[Document]:
        """Perform dense vector search and return LangChain Documents.

        Embeds ``query`` with the configured ``embedding_model``, then runs an
        ANN search against the LanceDB table.  Results are returned as
        LangChain ``Document`` objects whose metadata mirrors the structure
        used by Milvus / Elasticsearch backends so the rest of the RAG server
        remains backend-agnostic.

        Parameters
        ----------
        query:
            Natural-language search query.
        collection_name:
            LanceDB table to search.
        vectorstore:
            Optional pre-initialised LangChain VectorStore.  When ``None``
            (default), ``get_langchain_vectorstore(collection_name)`` is called
            lazily — matching the pattern used by ElasticVDB / MilvusVDB.
        top_k:
            Maximum number of results to return.
        filter_expr:
            Not currently applied — reserved for future SQL-predicate support.
        otel_ctx:
            OpenTelemetry context token (ignored — no tracing for LanceDB).
        """
        if vectorstore is None:
            vectorstore = self.get_langchain_vectorstore(collection_name)

        logger.info(
            "LanceDB Retrieval: querying table '%s', top_k=%d.", collection_name, top_k
        )

        try:
            start_time = time.time()

            logger.info(
                "  [Embedding] Generating query embedding for retrieval...")
            logger.info("  [Embedding] Query: '%s'",
                        query[:100] if query else "")
            retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})
            logger.info("  [Embedding] Query embedding generated successfully")

            retriever_lambda = RunnableLambda(lambda x: retriever.invoke(x))
            retriever_chain = {"context": retriever_lambda} | RunnableAssign(
                {"context": lambda input: input["context"]}
            )

            logger.info(
                "  [VDB Search] Performing vector similarity search in collection...")
            retriever_docs = retriever_chain.invoke(
                query, config={"run_name": "retriever"}
            )
            docs = retriever_docs.get("context", [])

            latency = time.time() - start_time
            logger.info(
                "  [VDB Search] Retrieved %d documents from table '%s'",
                len(docs),
                collection_name,
            )
            logger.info(
                "  [VDB Search] Total VDB operation latency: %.4f seconds", latency)

            docs = self._hydrate_document_identity(docs, collection_name)
            return self._add_collection_name_to_retreived_docs(docs, collection_name)

        except (requests.exceptions.ConnectionError, ConnectionError, OSError) as e:
            embedding_url = (
                self.embedding_model._client.base_url
                if hasattr(self.embedding_model, "_client")
                else "configured endpoint"
            )
            error_msg = (
                f"Embedding NIM unavailable at {embedding_url}. "
                "Please verify the service is running and accessible."
            )
            logger.error("Connection error in retrieval_langchain: %s", e)
            raise APIError(
                error_msg, ErrorCodeMapping.SERVICE_UNAVAILABLE) from e
        finally:
            # The LangChain embedding object is a long-lived client, not an
            # HTTP response. Do not close/clear it after every query.
            pass

    def get_langchain_vectorstore(
        self,
        collection_name: str,
    ) -> VectorStore:
        """Return a LangChain-compatible VectorStore backed by a LanceDB table.

        Returns a ``NRLLanceDB`` instance — a subclass of
        ``langchain_community.vectorstores.LanceDB`` that overrides
        ``results_to_docs`` to correctly parse NRL's non-standard metadata
        storage format (``str(meta)`` Python repr, not JSON).

        See ``nvidia_rag.utils.vdb.lancedb.nrl_lancedb.NRLLanceDB``
        for the full documentation of the metadata handling.
        """
        # NRLLanceDB lives in a sibling module.  Import here (not at module
        # level) because importing langchain_community.vectorstores.LanceDB
        # pulls in the lancedb package, which is not fork-safe.
        # from nvidia_rag.utils.vdb.lancedb.nrl_lancedb import NRLLanceDB  # noqa: PLC0415
        # from langchain_community.vectorstores import LanceDB
        # from nemo_retriever.common.vdb.lancedb import LanceDB

        lancedb_mod = _import_lancedb()

        try:
            db = lancedb_mod.connect(self.uri)
        except Exception as exc:
            raise RuntimeError(
                f"get_langchain_vectorstore: failed to connect to LanceDB at '{self.uri}': {exc}"
            ) from exc

        # Pass the LanceDBConnection object (not a LanceTable).
        # langchain_community >= 0.3 deprecated accepting a LanceTable directly.
        return NRLLanceDB(
            connection=db,
            embedding=self.embedding_model,
            vector_key="vector",
            id_key="id",
            text_key="text",
            table_name=collection_name,
        )

    def retrieve_chunks_by_filter(
        self,
        collection_name: str,
        source_name: str,
        page_numbers: list[int],
        limit: int = 1000,
    ) -> list[Document]:
        """Retrieve ALL chunks matching (source, page_numbers) via filter-only query.

        No semantic search — used for page-context expansion when
        ``fetch_full_page_context`` is enabled.

        Filters rows by matching the ``path`` or ``source_id`` column against
        ``source_name``, then parses the NRL ``metadata`` column to filter by
        ``page_number``.  Both operations run in Python/pandas (no ANN index).

        Parameters
        ----------
        collection_name:
            LanceDB table to query.
        source_name:
            Source document path to filter on.
        page_numbers:
            Page numbers to include (matched against the NRL metadata field).
        limit:
            Maximum number of chunks to return.
        """
        if not page_numbers:
            return []

        lancedb_mod = _import_lancedb()

        try:
            db = lancedb_mod.connect(self.uri)
            table = db.open_table(collection_name)
            df = table.to_pandas()
        except Exception as exc:
            logger.error(
                "retrieve_chunks_by_filter: failed to open table '%s': %s", collection_name, exc)
            return []

        # Filter by source path using path or source_id column
        import pandas as pd  # noqa: PLC0415

        source_mask = pd.Series([False] * len(df), index=df.index)
        if "path" in df.columns:
            source_mask |= df["path"].astype(str) == source_name
        if "source_id" in df.columns:
            source_mask |= df["source_id"].astype(str) == source_name

        filtered_df = df[source_mask]
        if filtered_df.empty:
            logger.debug(
                "retrieve_chunks_by_filter: no rows matching source '%s' in table '%s'.",
                source_name,
                collection_name,
            )
            return []

        # Further filter by page number from NRL metadata
        page_numbers_set = set(page_numbers)
        docs: list[Document] = []

        for _, row in filtered_df.iterrows():
            if len(docs) >= limit:
                break

            raw_meta = row.get("metadata", "")
            parsed_meta = _parse_nrl_metadata(raw_meta)

            # Try several common field names for page number
            page_num = (
                parsed_meta.get("page_number")
                or parsed_meta.get("page_num")
                or parsed_meta.get("page")
            )

            # If no page_number in metadata, include the chunk regardless
            # (avoids dropping all results for schemas that don't record page_number)
            if page_num is not None and page_num not in page_numbers_set:
                continue

            text = str(row.get("text", "")) if row.get(
                "text") is not None else ""
            source_val = row.get("path") or row.get("source_id", source_name)
            metadata = {
                "source": source_val,
                "content_metadata": parsed_meta,
            }
            docs.append(Document(page_content=text, metadata=metadata))

        return self._add_collection_name_to_retreived_docs(docs, collection_name)

    def retrieval_image_langchain(
        self,
        query: str,
        collection_name: str,
        vectorstore: VectorStore | None = None,
        top_k: int = 10,
        reranker_top_k: int | None = None,
    ) -> list[Document]:
        """Retrieve documents from a collection using an image query.

        Embeds the image query via the configured embedding model, performs a
        vector similarity search to find the most relevant document page, then
        returns all chunks from that page for multimodal context.

        Args:
            query: The image query (base64-encoded string or URL).
            collection_name: Name of the LanceDB table to search.
            vectorstore: Optional pre-initialised VectorStore.
            top_k: Number of results for the initial similarity search.
            reranker_top_k: Final number of documents to return.
                            Defaults to ``top_k`` when ``None``.
        """
        final_limit = reranker_top_k if reranker_top_k is not None else top_k

        if vectorstore is None:
            vectorstore = self.get_langchain_vectorstore(collection_name)

        try:
            embedding = self._embedding_model.embed_documents([query])
            scored = vectorstore.similarity_search_by_vector_with_relevance_scores(
                embedding=embedding[0],
                k=top_k,
            )
            results = [doc for doc, _ in scored]
        except Exception as exc:
            logger.error(
                "retrieval_image_langchain: error generating embeddings or searching: %s",
                exc,
                exc_info=True,
            )
            return []
        finally:
            # Keep the embedding client alive for subsequent requests.
            pass

        if not results:
            return []

        # Extract source and page from the top result
        try:
            top_meta = results[0].metadata

            # NRL metadata is stored under the "metadata" key (parsed dict) or
            # directly on the document metadata depending on NRLLanceDB version.
            nrl_meta = top_meta.get("metadata", {})
            if isinstance(nrl_meta, str):
                nrl_meta = _parse_nrl_metadata(nrl_meta)

            # Source name: prefer path > source_id > "source" key
            source_name = (
                top_meta.get("path")
                or top_meta.get("source_id")
                or nrl_meta.get("source_path")
                or nrl_meta.get("source_name")
                or ""
            )

            # Page number: look in NRL metadata
            page_number = (
                nrl_meta.get("page_number")
                or nrl_meta.get("page_num")
                or nrl_meta.get("page")
            )
        except (KeyError, IndexError, TypeError) as exc:
            logger.error(
                "retrieval_image_langchain: error accessing metadata from search results: %s",
                exc,
            )
            return []

        if not source_name:
            logger.warning(
                "retrieval_image_langchain: could not determine source name from top result metadata."
            )
            return self._add_collection_name_to_retreived_docs(
                results[:final_limit], collection_name
            )

        page_numbers = [page_number] if page_number is not None else []
        return self.retrieve_chunks_by_filter(
            collection_name=collection_name,
            source_name=source_name,
            page_numbers=page_numbers,
            limit=final_limit,
        )

    # ------------------------------------------------------------------
    # Metadata Schema Management
    # ------------------------------------------------------------------

    def create_metadata_schema_collection(self) -> None:
        """Create the ``metadata_schema`` system table if it does not exist.

        The table uses a simple two-column schema:
        - ``collection_name`` (string): the user collection this schema belongs to.
        - ``metadata_schema`` (string): JSON-serialised list of schema field dicts.
        """
        if self._metadata_schema_collection_initialized:
            return

        lancedb_mod = _import_lancedb()
        import pyarrow as pa  # noqa: PLC0415

        self.uri.mkdir(parents=True, exist_ok=True)
        db = lancedb_mod.connect(self.uri)

        if DEFAULT_METADATA_SCHEMA_COLLECTION not in db.table_names():
            schema = pa.schema([
                pa.field("collection_name", pa.string()),
                pa.field("metadata_schema", pa.string()),
            ])
            empty = pa.table(
                {
                    "collection_name": pa.array([], type=pa.string()),
                    "metadata_schema": pa.array([], type=pa.string()),
                },
                schema=schema,
            )
            db.create_table(
                DEFAULT_METADATA_SCHEMA_COLLECTION,
                data=empty,
                schema=schema,
                mode="create",
            )
            logger.info(
                "Created LanceDB metadata schema table '%s' at '%s'.",
                DEFAULT_METADATA_SCHEMA_COLLECTION,
                self.uri,
            )
        else:
            logger.debug(
                "LanceDB metadata schema table '%s' already exists.",
                DEFAULT_METADATA_SCHEMA_COLLECTION,
            )

        self._metadata_schema_collection_initialized = True

    def add_metadata_schema(
        self,
        collection_name: str,
        metadata_schema: list[dict[str, Any]],
    ) -> None:
        """Store (or replace) the metadata schema for ``collection_name``.

        Deletes any existing schema entry for the collection before inserting
        the new one, so this is effectively an upsert.

        Parameters
        ----------
        collection_name:
            The user collection whose schema is being recorded.
        metadata_schema:
            List of field definition dicts (same format as Milvus / Elasticsearch).
        """
        self.create_metadata_schema_collection()

        lancedb_mod = _import_lancedb()
        import pyarrow as pa  # noqa: PLC0415

        db = lancedb_mod.connect(self.uri)
        table = db.open_table(DEFAULT_METADATA_SCHEMA_COLLECTION)

        # Delete existing entry for this collection
        escaped = collection_name.replace("'", "\\'")
        try:
            table.delete(f"collection_name = '{escaped}'")
        except Exception as exc:
            logger.debug(
                "add_metadata_schema: delete attempt for '%s' raised: %s (may not exist yet).",
                collection_name,
                exc,
            )

        # Insert new schema row
        new_row = pa.table(
            {
                "collection_name": pa.array([collection_name], type=pa.string()),
                "metadata_schema": pa.array([json.dumps(metadata_schema)], type=pa.string()),
            }
        )
        table.add(new_row)
        logger.info(
            "Metadata schema stored for collection '%s': %s",
            collection_name,
            metadata_schema,
        )

    def get_metadata_schema(
        self,
        collection_name: str,
    ) -> list[dict[str, Any]]:
        """Retrieve the metadata schema for ``collection_name``.

        Returns an empty list if no schema has been registered or if the
        system table does not exist yet.
        """
        lancedb_mod = _import_lancedb()

        try:
            db = lancedb_mod.connect(self.uri)
            if DEFAULT_METADATA_SCHEMA_COLLECTION not in db.table_names():
                return []
            table = db.open_table(DEFAULT_METADATA_SCHEMA_COLLECTION)
            df = table.to_pandas()
        except Exception as exc:
            logger.error(
                "get_metadata_schema: error reading system table for '%s': %s",
                collection_name,
                exc,
            )
            return []

        row = df[df["collection_name"] == collection_name]
        if row.empty:
            logger.info(
                "get_metadata_schema: no schema found for collection '%s'.",
                collection_name,
            )
            return []
        try:
            return json.loads(row.iloc[0]["metadata_schema"])
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.error(
                "get_metadata_schema: failed to parse schema for '%s': %s",
                collection_name,
                exc,
            )
            return []

    # ------------------------------------------------------------------
    # Document Info Management
    # ------------------------------------------------------------------

    def create_document_info_collection(self) -> None:
        """Create the ``document_info`` system table if it does not exist.

        The table schema has four columns:
        - ``info_type`` (string): "catalog", "collection", or "document".
        - ``collection_name`` (string): which user collection the info belongs to.
        - ``document_name`` (string): document filename or "NA" for collection-level info.
        - ``info_value`` (string): JSON-serialised info dict.
        """
        if self._document_info_collection_initialized:
            return

        lancedb_mod = _import_lancedb()
        import pyarrow as pa  # noqa: PLC0415

        Path(self.uri).mkdir(parents=True, exist_ok=True)
        db = lancedb_mod.connect(self.uri)

        if DEFAULT_DOCUMENT_INFO_COLLECTION not in db.table_names():
            schema = pa.schema([
                pa.field("info_type", pa.string()),
                pa.field("collection_name", pa.string()),
                pa.field("document_name", pa.string()),
                pa.field("info_value", pa.string()),
            ])
            empty = pa.table(
                {
                    "info_type": pa.array([], type=pa.string()),
                    "collection_name": pa.array([], type=pa.string()),
                    "document_name": pa.array([], type=pa.string()),
                    "info_value": pa.array([], type=pa.string()),
                },
                schema=schema,
            )
            db.create_table(
                DEFAULT_DOCUMENT_INFO_COLLECTION,
                data=empty,
                schema=schema,
                mode="create",
            )
            logger.info(
                "Created LanceDB document info table '%s' at '%s'.",
                DEFAULT_DOCUMENT_INFO_COLLECTION,
                self.uri,
            )
        else:
            logger.debug(
                "LanceDB document info table '%s' already exists.",
                DEFAULT_DOCUMENT_INFO_COLLECTION,
            )

        self._document_info_collection_initialized = True

    def _get_aggregated_document_info(
        self,
        collection_name: str,
        info_value: dict[str, Any],
    ) -> dict[str, Any]:
        """Aggregate new collection-level info with existing info.

        Used internally by ``add_document_info`` when ``info_type == "collection"``
        to merge new ingestion statistics with any already-stored values (e.g. to
        accumulate counts across multiple ingestion calls).

        Parameters
        ----------
        collection_name:
            The user collection whose aggregated info is needed.
        info_value:
            The new info dict from the current ingestion.

        Returns
        -------
        dict
            Merged dict produced by ``perform_document_info_aggregation``.
        """
        existing = self.get_document_info(
            info_type="collection",
            collection_name=collection_name,
            document_name="NA",
        )
        try:
            return perform_document_info_aggregation(existing, info_value)
        except Exception as exc:
            logger.error(
                "_get_aggregated_document_info: aggregation failed for '%s': %s",
                collection_name,
                exc,
            )
            return info_value

    def add_document_info(
        self,
        info_type: str,
        collection_name: str,
        document_name: str,
        info_value: dict[str, Any],
    ) -> None:
        """Store (or replace) document info for a collection or document.

        For ``info_type == "collection"`` the new ``info_value`` is aggregated
        with any existing collection-level info using
        ``perform_document_info_aggregation`` before storage (same semantics as
        Milvus and Elasticsearch).

        Parameters
        ----------
        info_type:
            One of ``"catalog"``, ``"collection"``, or ``"document"``.
        collection_name:
            Target user collection.
        document_name:
            Document filename, or ``"NA"`` for collection/catalog-level entries.
        info_value:
            Info dict to store.
        """
        self.create_document_info_collection()

        # Aggregate collection-level info with existing data before storing
        if info_type == "collection":
            info_value = self._get_aggregated_document_info(
                collection_name, info_value)

        lancedb_mod = _import_lancedb()
        import pyarrow as pa  # noqa: PLC0415

        db = lancedb_mod.connect(self.uri)
        table = db.open_table(DEFAULT_DOCUMENT_INFO_COLLECTION)

        # Delete existing entry for this (info_type, collection_name, document_name)
        esc_type = info_type.replace("'", "\\'")
        esc_col = collection_name.replace("'", "\\'")
        esc_doc = document_name.replace("'", "\\'")
        try:
            table.delete(
                f"info_type = '{esc_type}' "
                f"AND collection_name = '{esc_col}' "
                f"AND document_name = '{esc_doc}'"
            )
        except Exception as exc:
            logger.debug(
                "add_document_info: delete attempt raised: %s (may not exist yet).", exc
            )

        # Insert new row
        new_row = pa.table(
            {
                "info_type": pa.array([info_type], type=pa.string()),
                "collection_name": pa.array([collection_name], type=pa.string()),
                "document_name": pa.array([document_name], type=pa.string()),
                "info_value": pa.array([json.dumps(info_value)], type=pa.string()),
            }
        )
        table.add(new_row)
        logger.debug(
            "Document info stored: info_type=%s, collection=%s, document=%s.",
            info_type,
            collection_name,
            document_name,
        )

    def get_document_info(
        self,
        info_type: str,
        collection_name: str,
        document_name: str,
    ) -> dict[str, Any]:
        """Retrieve document info from the ``document_info`` system table.

        Returns an empty dict when no matching entry is found or when the
        system table does not exist yet.

        Parameters
        ----------
        info_type:
            One of ``"catalog"``, ``"collection"``, or ``"document"``.
        collection_name:
            Target user collection.
        document_name:
            Document filename, or ``"NA"`` for collection/catalog-level entries.
        """
        lancedb_mod = _import_lancedb()

        try:
            db = lancedb_mod.connect(self.uri)
            if DEFAULT_DOCUMENT_INFO_COLLECTION not in db.table_names():
                return {}
            table = db.open_table(DEFAULT_DOCUMENT_INFO_COLLECTION)
            df = table.to_pandas()
        except Exception as exc:
            logger.error(
                "get_document_info: error reading system table for '%s/%s/%s': %s",
                info_type,
                collection_name,
                document_name,
                exc,
            )
            return {}

        mask = (
            (df["info_type"] == info_type)
            & (df["collection_name"] == collection_name)
            & (df["document_name"] == document_name)
        )
        rows = df[mask]
        if rows.empty:
            logger.debug(
                "get_document_info: no entry for info_type=%s, collection=%s, document=%s.",
                info_type,
                collection_name,
                document_name,
            )
            return {}
        try:
            return json.loads(rows.iloc[0]["info_value"])
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.error(
                "get_document_info: failed to parse info_value for '%s/%s/%s': %s",
                info_type,
                collection_name,
                document_name,
                exc,
            )
            return {}

    # ------------------------------------------------------------------
    # Catalog Metadata
    # ------------------------------------------------------------------

    def get_catalog_metadata(self, collection_name: str) -> dict[str, Any]:
        """Get catalog metadata for a collection.

        Wraps ``get_document_info`` with ``info_type="catalog"`` and
        ``document_name="NA"``, consistent with Milvus / Elasticsearch.
        """
        return self.get_document_info(
            info_type="catalog",
            collection_name=collection_name,
            document_name="NA",
        )

    def update_catalog_metadata(
        self,
        collection_name: str,
        updates: dict[str, Any],
    ) -> None:
        """Update catalog metadata for a collection.

        Merges ``updates`` into the existing catalog metadata dict and
        refreshes the ``last_updated`` timestamp before saving.
        """
        existing = self.get_catalog_metadata(collection_name)
        merged = {**existing, **updates}
        merged["last_updated"] = get_current_timestamp()
        self.add_document_info(
            info_type="catalog",
            collection_name=collection_name,
            document_name="NA",
            info_value=merged,
        )

    def get_document_catalog_metadata(
        self,
        collection_name: str,
        document_name: str,
    ) -> dict[str, Any]:
        """Get catalog metadata (description and tags) for a document.

        Returns a dict with keys ``"description"`` (str) and ``"tags"``
        (list), consistent with Milvus / Elasticsearch behaviour.
        """
        doc_info = self.get_document_info(
            info_type="document",
            collection_name=collection_name,
            document_name=document_name,
        )
        return {
            "description": doc_info.get("description", ""),
            "tags": doc_info.get("tags", []),
        }

    def update_document_catalog_metadata(
        self,
        collection_name: str,
        document_name: str,
        updates: dict[str, Any],
    ) -> None:
        """Update catalog metadata for a specific document.

        Only ``"description"`` and ``"tags"`` keys from ``updates`` are applied;
        all other existing fields are preserved.
        """
        existing = self.get_document_info(
            info_type="document",
            collection_name=collection_name,
            document_name=document_name,
        )
        for key in ["description", "tags"]:
            if key in updates:
                existing[key] = updates[key]
        self.add_document_info(
            info_type="document",
            collection_name=collection_name,
            document_name=document_name,
            info_value=existing,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _delete_from_system_table(
        self,
        system_table: str,
        filter_col: str,
        filter_val: str,
    ) -> None:
        """Delete all rows in a system table where ``filter_col == filter_val``.

        Silently ignores errors (e.g. table does not exist).
        """
        lancedb_mod = _import_lancedb()
        try:
            db = lancedb_mod.connect(self.uri)
            if system_table not in db.table_names():
                return
            table = db.open_table(system_table)
            escaped = filter_val.replace("'", "\\'")
            table.delete(f"{filter_col} = '{escaped}'")
        except Exception as exc:
            logger.debug(
                "_delete_from_system_table: error deleting from '%s' where %s='%s': %s",
                system_table,
                filter_col,
                filter_val,
                exc,
            )

    def _delete_document_info_entry(
        self,
        collection_name: str,
        document_name: str,
        info_type: str,
    ) -> None:
        """Delete a specific entry from the document_info system table."""
        lancedb_mod = _import_lancedb()
        try:
            db = lancedb_mod.connect(self.uri)
            if DEFAULT_DOCUMENT_INFO_COLLECTION not in db.table_names():
                return
            table = db.open_table(DEFAULT_DOCUMENT_INFO_COLLECTION)
            esc_type = info_type.replace("'", "\\'")
            esc_col = collection_name.replace("'", "\\'")
            esc_doc = document_name.replace("'", "\\'")
            table.delete(
                f"info_type = '{esc_type}' "
                f"AND collection_name = '{esc_col}' "
                f"AND document_name = '{esc_doc}'"
            )
        except Exception as exc:
            logger.debug(
                "_delete_document_info_entry: error for collection='%s', document='%s': %s",
                collection_name,
                document_name,
                exc,
            )

    def _get_document_info_map(self, collection_name: str) -> dict[str, dict[str, Any]]:
        """Return a ``{document_name: info_value}`` map for ``info_type="document"``.

        Used by ``get_documents`` to attach per-document info without making a
        separate ``get_document_info`` call per document.
        """
        lancedb_mod = _import_lancedb()
        result: dict[str, dict[str, Any]] = {}
        try:
            db = lancedb_mod.connect(self.uri)
            if DEFAULT_DOCUMENT_INFO_COLLECTION not in db.table_names():
                return result
            table = db.open_table(DEFAULT_DOCUMENT_INFO_COLLECTION)
            df = table.to_pandas()
            mask = (df["info_type"] == "document") & (
                df["collection_name"] == collection_name)
            for _, row in df[mask].iterrows():
                doc_name = row["document_name"]
                try:
                    result[doc_name] = json.loads(row["info_value"])
                except (json.JSONDecodeError, KeyError):
                    result[doc_name] = {}
        except Exception as exc:
            logger.error(
                "_get_document_info_map: error for collection '%s': %s",
                collection_name,
                exc,
            )
        return result

    @staticmethod
    def _add_collection_name_to_retreived_docs(
        docs: list[Document], collection_name: str
    ) -> list[Document]:
        """Attach ``collection_name`` to each Document's metadata."""
        for doc in docs:
            doc.metadata["collection_name"] = collection_name
        return docs
