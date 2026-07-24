import json
import logging
from datetime import datetime

from app.memory.lancedb_storage import LanceDBStorage
from app.memory.types import MemoryRecord
from app.record_processor.models import KnowledgeEntry

logger = logging.getLogger(__name__)

TABLE_NAME = "record_knowledge"

_storage: LanceDBStorage | None = None


def _get_storage() -> LanceDBStorage:
    global _storage
    if _storage is None:
        _storage = LanceDBStorage(table_name=TABLE_NAME)
    return _storage


def _entry_to_memory_record(entry: KnowledgeEntry) -> MemoryRecord:
    return MemoryRecord(
        id=entry.knowledge_id,
        content=entry.summary,
        scope=f"/{entry.business_id}/{entry.record_id}",
        categories=[entry.content_type],
        metadata={
            "business_id": entry.business_id,
            "record_id": entry.record_id,
            "content_type": entry.content_type,
            "version": entry.version,
            "structured_metadata": json.dumps(entry.structured_metadata),
        },
        importance=0.7,
        created_at=datetime.utcnow(),
        last_accessed=datetime.utcnow(),
        embedding=entry.embedding,
        source="record_knowledge",
        private=False,
    )


def insert(entry: KnowledgeEntry) -> None:
    storage = _get_storage()
    record = _entry_to_memory_record(entry)
    storage.save([record])


def delete_by_record(business_id: str, record_id: str) -> bool:
    storage = _get_storage()
    try:
        scope_prefix = f"/{business_id}/{record_id}"
        storage.delete(scope_prefix=scope_prefix)
        return True
    except Exception as e:
        logger.warning(f"Failed to delete knowledge entries: {e}")
        return False
