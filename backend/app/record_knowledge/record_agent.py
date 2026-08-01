import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.embeddings.client import get_embedding_client
from app.memory.lancedb import LanceDBStorage
from app.memory.memory import MemoryRecord
from app.record_knowledge.config import get_record_knowledge_config
from app.record_knowledge.models import RecordContentInput, KnowledgeEntry, ProcessingResult, AIUnderstanding
from app.record_knowledge.summarizers import SUMMARIZERS

logger = logging.getLogger(__name__)

_storage_cache: dict[str, LanceDBStorage] = {}


def _get_record_storage(business_id: str) -> LanceDBStorage:
    """Get or create the LanceDB storage for record knowledge, keyed by business_id."""
    if business_id not in _storage_cache:
        _storage_cache[business_id] = LanceDBStorage(business_id=business_id)
    return _storage_cache[business_id]


def _entry_to_record(entry: KnowledgeEntry) -> MemoryRecord:
    """Convert a KnowledgeEntry to a MemoryRecord for storage.

    Separates multimodal data (images, audio, videos) from metadata.
    These go into their own binary columns, not into the JSON metadata field.
    """
    images: list[str] = []
    audio: list[str] = []
    videos: list[str] = []

    # Extract multimodal data from structured_metadata
    structured = entry.structured_metadata if isinstance(entry.structured_metadata, dict) else {}
    if "images" in structured:
        raw_images = structured["images"]
        if isinstance(raw_images, list):
            images = raw_images

    if "audio" in structured:
        raw_audio = structured["audio"]
        if isinstance(raw_audio, list):
            audio = raw_audio

    if "videos" in structured:
        raw_videos = structured["videos"]
        if isinstance(raw_videos, list):
            videos = raw_videos

    # Build clean metadata without multimodal blobs
    clean_metadata = {
        "content_type": entry.content_type,
        "version": entry.version,
    }
    # Copy non-multimodal fields from structured_metadata
    for key, value in structured.items():
        if key not in ("images", "audio", "videos"):
            clean_metadata[key] = value

    return MemoryRecord(
        id=entry.knowledge_id,
        content=entry.summary,
        scope=f"/{entry.business_id}/record/{entry.record_id}",
        metadata=clean_metadata,
        images=images,
        audio=audio,
        videos=videos,
        created_at=datetime.now(timezone.utc),
        embedding=entry.embedding,
    )


_insight_agent = None


def _get_insight_agent():
    global _insight_agent
    if _insight_agent is None:
        from app.agents.models import Agent
        _insight_agent = Agent.from_spec("record_insight")
    return _insight_agent


async def process_record_content(record_content: RecordContentInput) -> ProcessingResult:
    summarizer = SUMMARIZERS.get(record_content.content_type)
    if summarizer is None:
        logger.warning(f"Unsupported content_type: {record_content.content_type}")
        return ProcessingResult(success=False, error=f"Unsupported content_type: {record_content.content_type}")

    try:
        result = await summarizer(record_content.content)

        if not result:
            return ProcessingResult(success=False, error="Processing failed: no content extracted")

        title = result.get("title", "")
        body = result.get("summary", "")
        full_content = result.get("content", "")
        page_chunks = result.get("page_chunks", [])

        embedding_client = get_embedding_client()
        now = datetime.now(timezone.utc).isoformat()

        from app.db.tools.records import update_record, get_record
        from app.db.client import get_client as get_db_client

        if body:
            db = get_db_client()
            db.table("record_content").update({"content": body, "status": "completed"}).eq("id", record_content.metadata.get("content_id", "")).eq("business_id", record_content.business_id).execute()
        else:
            db = get_db_client()
            db.table("record_content").update({"status": "completed"}).eq("id", record_content.metadata.get("content_id", "")).eq("business_id", record_content.business_id).execute()

        if title:
            record = await get_record(record_content.business_id, record_content.record_id)
            if record and (record.get("title", "").startswith("#") or record.get("title") == "Untitled"):
                await update_record(record_content.business_id, record_content.record_id, title=title)

        if page_chunks:
            for chunk in page_chunks:
                chunk_text = chunk.get("text", "")
                if not chunk_text:
                    continue
                chunk_metadata = {
                    "page_number": chunk.get("page_number"),
                    "pages_covered": chunk.get("pages_covered", []),
                }
                json_blocks = chunk.get("json_blocks", [])
                if json_blocks:
                    chunk_metadata["json_blocks"] = json_blocks
                chunk_images = chunk.get("images", [])
                if chunk_images:
                    chunk_metadata["images"] = chunk_images

                page_embedding = await embedding_client.aembed_query(chunk_text, input_type="passage")
                page_entry = KnowledgeEntry(
                    knowledge_id=str(uuid4()),
                    business_id=record_content.business_id,
                    record_id=record_content.record_id,
                    content_type="pdf_page",
                    summary=chunk_text,
                    structured_metadata=chunk_metadata,
                    embedding=page_embedding,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
                store = _get_record_storage(record_content.business_id)
                store.save([_entry_to_record(page_entry)])
            logger.info(f"Embedded {len(page_chunks)} PDF page chunks for record {record_content.record_id}")

        embed_text = full_content if full_content else body
        if not embed_text:
            embed_text = title

        saved_content = f"{title}\n\n{body}" if body else title

        structured_meta = record_content.metadata.copy() if record_content.metadata else {}
        structured_meta["title"] = title
        if full_content and full_content != body:
            structured_meta["full_content_type"] = record_content.content_type

        logger.info(f"Processed content for record {record_content.record_id}")

        embedding = await embedding_client.aembed_query(embed_text, input_type="passage")
        entry = KnowledgeEntry(
            knowledge_id=str(uuid4()),
            business_id=record_content.business_id,
            record_id=record_content.record_id,
            content_type=record_content.content_type,
            summary=saved_content,
            structured_metadata=structured_meta,
            embedding=embedding,
            version=1,
            created_at=now,
            updated_at=now,
        )

        _get_record_storage(record_content.business_id).save([_entry_to_record(entry)])

        # Generate 2 suggested questions based on the processed content
        suggested_questions = await _generate_suggestions(saved_content)

        return ProcessingResult(success=True, entry=entry, suggested_questions=suggested_questions)

    except Exception as e:
        logger.error(f"Failed to process record content for {record_content.record_id}: {e}", exc_info=True)
        return ProcessingResult(success=False, error=str(e))


async def _generate_suggestions(content: str) -> list[str]:
    """Generate max 2 suggested follow-up questions based on processed content."""
    from app.llm.client import get_client as get_llm_client

    try:
        llm = get_llm_client()
        messages = [
            {"role": "system", "content": "Generate exactly 2 short follow-up questions a user might ask about this content. Return only the questions separated by a newline. No numbering."},
            {"role": "user", "content": content[:2000]},
        ]
        response = await llm.ainvoke(messages)
        raw = response.content.strip() if response.content else ""
        questions = [q.strip() for q in raw.split("\n") if q.strip()][:2]
        return questions
    except Exception as e:
        logger.warning(f"Suggestion generation failed: {e}")
        return []


async def get_record_understanding(business_id: str, record_id: str) -> dict:
    """Generate full overview of a record using the understanding agent.
    
    Returns: {"insight": str, "suggestions": list[str]}
    """
    from app.record_knowledge.understanding_agent import run_understanding_agent

    try:
        return await run_understanding_agent(business_id, record_id)
    except Exception as e:
        logger.error(f"Understanding generation failed: {e}", exc_info=True)
        return {"insight": "", "suggestions": []}
