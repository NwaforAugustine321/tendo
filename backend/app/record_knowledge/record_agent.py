import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

# from app.embeddings.client import get_embedding_client
# from app.memory.lancedb import LanceDBStorage
# from app.memory.memory import MemoryRecord
# from app.record_knowledge.extractors import extract_content
from app.record_knowledge.config import get_record_knowledge_config
from app.record_knowledge.models import RecordContentInput, KnowledgeEntry, ProcessingResult, AIUnderstanding
from app.record_knowledge.summarizers import SUMMARIZERS
# from app.scheduler.jobs.record_processing import schedule_extraction

from app.runtime.rag.ingestion.default_loader import DefaultDocumentLoader
from app.runtime.rag.ingestion.default_splitter import DefaultDocumentSplitter
from app.runtime.rag.ingestion.pipeline import DocumentIngestionPipeline
from app.runtime.rag.lancedb import LanceRAGStore

logger = logging.getLogger(__name__)

# _storage_cache: dict[str, LanceDBStorage] = {}

_insight_agent = None


def _get_insight_agent():
    global _insight_agent
    if _insight_agent is None:
        from app.agents.models import Agent
        _insight_agent = Agent.from_spec("record_insight")
    return _insight_agent


async def process_record_content(record_content: RecordContentInput) -> ProcessingResult:
    try:
        raw_content = record_content.content or ""
        content_type = record_content.content_type
        content_id = record_content.metadata.get(
            "content_id", "") if record_content.metadata else ""
        record_id = record_content.record_id
        business_id = record_content.business_id
        file_url = record_content.file_url or ""

        if not raw_content and not file_url:
            return ProcessingResult(success=False, error="No content to process")

        store = LanceRAGStore(namespace=business_id)

        pipeline = DocumentIngestionPipeline(
            loader=DefaultDocumentLoader(),
            splitter=DefaultDocumentSplitter(),
            store=store,
        )

        # Determine source:
        # - file_url for media files (audio, images, PDFs)
        # - raw_content if it looks like a path/URL with extension
        # - Otherwise write plain text to a temp .txt file
        import tempfile
        import os
        from pathlib import Path

        source = file_url or raw_content
        logger.info(f"Ingestion source: {source[:100]}")
        source_path = Path(source)
        has_extension = bool(source_path.suffix)
        logger.info(
            f"Ingestion extension detected: '{source_path.suffix}', has_extension={has_extension}")
        temp_file = None

        if not has_extension and raw_content.strip():
            # Plain text content — write to temp .txt file
            tmp = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                delete=False,
                encoding="utf-8",
            )
            tmp.write(raw_content)
            tmp.close()
            source = tmp.name
            temp_file = tmp.name

        result = await pipeline.ingest(
            source=source,
        )

        logger.info(
            f"Ingestion complete: {result.documents} docs, {result.chunks} chunks"
        )

        logger.info(
            f"Ingestion entries preview: {[e.content[:50] for e in result.entries[:3]]}"
        )

        # Cleanup temp file if created
        if temp_file:
            try:
                os.unlink(temp_file)
            except Exception:
                pass

        if result.chunks == 0:
            return ProcessingResult(success=False, error="No chunks produced from content")

        return ProcessingResult(success=True, entry=None, suggested_questions=[])

    except Exception as e:
        logger.error(
            f"Failed to process the content for the record: {e}", exc_info=True)
        return ProcessingResult(success=False, error=str(e))


async def get_record_understanding(business_id: str, record_id: str) -> dict:

    from app.record_knowledge.understanding_agent import run_understanding_agent

    try:
        return await run_understanding_agent(business_id, record_id)
    except Exception as e:
        logger.error(f"Understanding generation failed: {e}", exc_info=True)
        return {"insight": "", "suggestions": []}
