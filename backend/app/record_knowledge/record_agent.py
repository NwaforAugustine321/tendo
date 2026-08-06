import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.embeddings.client import get_embedding_client
from app.memory.lancedb import LanceDBStorage
from app.memory.memory import MemoryRecord
from app.record_knowledge.extractors import extract_content
from app.record_knowledge.config import get_record_knowledge_config
from app.record_knowledge.models import RecordContentInput, KnowledgeEntry, ProcessingResult, AIUnderstanding
from app.record_knowledge.summarizers import SUMMARIZERS
from app.scheduler.jobs.record_processing import schedule_extraction

logger = logging.getLogger(__name__)

_storage_cache: dict[str, LanceDBStorage] = {}

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
        content_id = record_content.metadata.get("content_id", "") if record_content.metadata else ""
        record_id = record_content.record_id

        embed_text = await schedule_extraction(
            business_id=record_content.business_id,
            record_id=record_id,
            content_type=content_type,
            content=raw_content,
            content_id=content_id,
            metadata=record_content.metadata,
        )

        if not embed_text or not embed_text.strip():
            return ProcessingResult(success=False, error="No content to process")

        return ProcessingResult(success=True, entry=None, suggested_questions=[])

    except Exception as e:
        logger.error(f"Failed to process the content for the record: {e}", exc_info=True)
        return ProcessingResult(success=False, error=str(e))


async def get_record_understanding(business_id: str, record_id: str) -> dict:

    from app.record_knowledge.understanding_agent import run_understanding_agent

    try:
        # return await run_understanding_agent(business_id, record_id)
        return {"insight": "", "suggestions": []}
    except Exception as e:
        logger.error(f"Understanding generation failed: {e}", exc_info=True)
        return {"insight": "", "suggestions": []}
