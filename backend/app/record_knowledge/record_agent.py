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

RECORD_KNOWLEDGE_TABLE = "record_knowledge"

_storage: LanceDBStorage | None = None


def _get_record_storage() -> LanceDBStorage:
    """Get or create the LanceDB storage for record knowledge."""
    global _storage
    if _storage is None:
        _storage = LanceDBStorage(table_name=RECORD_KNOWLEDGE_TABLE)
    return _storage


def _entry_to_record(entry: KnowledgeEntry) -> MemoryRecord:
    """Convert a KnowledgeEntry to a MemoryRecord for storage."""
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
        created_at=datetime.now(timezone.utc),
        last_accessed=datetime.now(timezone.utc),
        embedding=entry.embedding,
        source="record_knowledge",
        private=False,
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

        # If summarizer returned empty, processing failed
        if not result:
            return ProcessingResult(success=False, error="Processing failed: no content extracted")

        # All summarizers return dict: {title, summary, content, page_chunks?}
        title = result.get("title", "")
        body = result.get("summary", "")
        full_content = result.get("content", "")
        page_chunks = result.get("page_chunks", []) 

        embedding_client = get_embedding_client()
        now = datetime.now(timezone.utc).isoformat()

        from app.db.tools.records import update_record, get_record
        from app.db.client import get_client as get_db_client

        # Save the summary text on the record_content entry (no prefixes)
        if body:
            db = get_db_client()
            db.table("record_content").update({"content": body, "status": "completed"}).eq("id", record_content.metadata.get("content_id", "")).eq("business_id", record_content.business_id).execute()
        else:
            db = get_db_client()
            db.table("record_content").update({"status": "completed"}).eq("id", record_content.metadata.get("content_id", "")).eq("business_id", record_content.business_id).execute()

        # Update record title if current title is generic
        if title:
            record = await get_record(record_content.business_id, record_content.record_id)
            if record and (record.get("title", "").startswith("#") or record.get("title") == "Untitled"):
                await update_record(record_content.business_id, record_content.record_id, title=title)

        # For PDF with page chunks: embed each page separately
        if page_chunks:
            for chunk in page_chunks:
                chunk_text = chunk.get("text", "")
                if not chunk_text:
                    continue
                page_embedding = await embedding_client.aembed_query(chunk_text, input_type="passage")
                page_entry = KnowledgeEntry(
                    knowledge_id=str(uuid4()),
                    business_id=record_content.business_id,
                    record_id=record_content.record_id,
                    content_type="pdf_page",
                    summary=chunk_text,
                    structured_metadata={
                        "page_number": chunk.get("page_number"),
                        "pages_covered": chunk.get("pages_covered", []),
                    },
                    embedding=page_embedding,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
                store = _get_record_storage()
                store.save([_entry_to_record(page_entry)])
            logger.info(f"Embedded {len(page_chunks)} PDF page chunks for record {record_content.record_id}")

        # Build embedding text (title + summary + content)
        if full_content:
            summary_text = f"Title: {title}\nSummary: {body}\nContent: {full_content}"
        else:
            summary_text = f"Title: {title}\nSummary: {body}"

        logger.info(f"Processed content for record {record_content.record_id}")

        embedding = await embedding_client.aembed_query(summary_text, input_type="passage")
        entry = KnowledgeEntry(
            knowledge_id=str(uuid4()),
            business_id=record_content.business_id,
            record_id=record_content.record_id,
            content_type=record_content.content_type,
            summary=summary_text,
            structured_metadata=record_content.metadata,
            embedding=embedding,
            version=1,
            created_at=now,
            updated_at=now,
        )

        _get_record_storage().save([_entry_to_record(entry)])

        return ProcessingResult(success=True, entry=entry)

    except Exception as e:
        logger.error(f"Failed to process record content for {record_content.record_id}: {e}", exc_info=True)
        return ProcessingResult(success=False, error=str(e))


async def get_record_understanding(business_id: str, record_id: str) -> str:
    """Generate full overview of a record by letting LLM search LanceDB multiple times."""
    from app.db.tools.record_tools import get_record_knowledge_tools
    from app.llm.client import get_client as get_llm_client
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

    tools = get_record_knowledge_tools(business_id, record_id)
    llm = get_llm_client()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = (
        "You have access to a search tool that retrieves content from this record's knowledge store.\n"
        "You MUST search multiple times with different queries to gather the full picture:\n"
        "- Search for the main topic or title\n"
        "- Search for details, specifics, data\n"
        "- Search for any other aspects you haven't covered yet\n\n"
        "After gathering enough information from multiple searches, write a full explanation covering everything in this record.\n\n"
        "Rules:\n"
        "- Cover ALL content found, not just one result.\n"
        "- Explain the main points, key details, and full understanding.\n"
        "- Write naturally, as if explaining to someone who hasn't seen it.\n"
        "- Do not invent or add information not found in the searches.\n"
        "- Do not start with 'This record...'.\n"
        "- Return only plain text. No JSON.\n"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Search for all content in this record and explain everything you find."),
    ]

    try:
        for _ in range(5):
            response = await llm_with_tools.ainvoke(messages)

            if response.tool_calls:
                messages.append(response)
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_fn = next((t for t in tools if t.name == tool_name), None)
                    if tool_fn:
                        result = await tool_fn.ainvoke(tool_args)
                        messages.append(ToolMessage(content=str(result)[:3000], tool_call_id=tool_call["id"]))
                continue

            raw = response.content if hasattr(response, "content") else str(response)
            return raw.strip() if raw else "Unable to generate overview at this time."

        # After max rounds, get final answer
        response = await llm.ainvoke(messages)
        raw = response.content if hasattr(response, "content") else str(response)
        return raw.strip() if raw else "Unable to generate overview at this time."

    except Exception as e:
        logger.error(f"Understanding generation failed: {e}", exc_info=True)
        return "Unable to generate overview at this time."
