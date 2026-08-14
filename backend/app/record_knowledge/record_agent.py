import json
import logging
from datetime import datetime, timezone
from uuid import uuid4
from app.record_knowledge.models import RecordContentInput, KnowledgeEntry, ProcessingResult, AIUnderstanding
from app.runtime.rag.ingestion.default_loader import DefaultDocumentLoader
from app.runtime.rag.ingestion.default_splitter import DefaultDocumentSplitter
from app.runtime.rag.ingestion.pipeline import DocumentIngestionPipeline
from app.runtime.rag.lancedb import LanceRAGStore
from app.llm.client import get_client
from app.runtime.llm_vendors.langchain import LangChainLLM
from app.runtime.agents.agent import Agent
from app.runtime.memory.factory import (
    create_memory_provider,
)
from app.runtime.rag.factory import (
    create_rag_provider
)
from app.runtime.utils.spec_loader import LoaderAgentSpec
from app.record_knowledge.summarizers import generate_record_summary, generate_record_overview

logger = logging.getLogger(__name__)


insight_specialist_spec = LoaderAgentSpec.from_spec(
    name='Insight Specialist', path='planner')

prompt = f"Role:\n{insight_specialist_spec.role}\n\nBackstory:\n{insight_specialist_spec.backstory}\n\nGoal:\n{insight_specialist_spec.goal}\n"

_llm_instance = None


def _get_llm():
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LangChainLLM(model=get_client())
    return _llm_instance


async def process_record_content(record_content: RecordContentInput) -> ProcessingResult:
    try:
        content = record_content.content or ""
        business_id = record_content.business_id
        record_id = record_content.record_id or ""
        file_url = record_content.file_url or ""

        if not content and not file_url:
            return ProcessingResult(success=False, error="No content to process")

        scopes = [f"business/{business_id}",
                  f"business/{business_id}/record/{record_id}"]

        store = LanceRAGStore(namespace=business_id, scopes=scopes)

        pipeline = DocumentIngestionPipeline(
            loader=DefaultDocumentLoader(),
            splitter=DefaultDocumentSplitter(),
            store=store,
        )

        source = content

        result = await pipeline.ingest(
            source=source,
            content_type=record_content.content_type,
        )

        if result.chunks == 0:
            return ProcessingResult(success=False, error="No chunks produced from content")

        MAX_CHUNKS = 10
        chunks = result.entries[:MAX_CHUNKS]
        rolling_summary = ""
        title = ""
        suggested_questions = []

        for chunk in chunks:
            if rolling_summary:
                text_to_summarize = f"[Previous Summary]\n{rolling_summary}\n\n[New Content]\n{chunk.content}"
            else:
                text_to_summarize = chunk.content
            summary_result = await generate_record_summary(text_to_summarize)
            title = summary_result.get("title", "") or title
            rolling_summary = summary_result.get("summary", "")
            suggested_questions = summary_result.get(
                "suggested_questions", []) or suggested_questions

        logger.info(
            f"Process complete: {result.documents} docs, {result.chunks} chunks"
        )

        return ProcessingResult(
            success=True,
            title=title,
            summary=rolling_summary,
            suggested_questions=suggested_questions,
        )

    except Exception as e:
        logger.error(
            f"Failed to process the content for the record: {e}", exc_info=True)
        return ProcessingResult(success=False, error=str(e))


async def get_record_understanding(business_id: str, record_id: str) -> dict:

    try:
        return await generate_record_overview(business_id, record_id)
    except Exception as e:
        logger.error(f"Understanding generation failed: {e}", exc_info=True)
        return {"insight": "", "suggestions": []}
