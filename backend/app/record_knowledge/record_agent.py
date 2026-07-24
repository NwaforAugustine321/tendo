import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.embeddings.client import get_embedding_client
from app.lib.json_parser import parse_json_output
from app.record_knowledge.config import get_record_knowledge_config
from app.record_knowledge.models import RecordContentInput, KnowledgeEntry, ProcessingResult, AIUnderstanding
from app.record_knowledge import store
from app.record_knowledge.summarizers import SUMMARIZERS

logger = logging.getLogger(__name__)


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
        summary = await summarizer(record_content.content)

        # If summarizer returned empty, processing failed
        if not summary or not summary.strip():
            return ProcessingResult(success=False, error="Processing failed: no content extracted")

        # For non-text content types, save the extracted summary on the content entry
        if record_content.content_type != "text" and "|||" in summary:
            from app.db.tools.records import update_record, get_record
            from app.db.client import get_client as get_db_client

            # Parse title|||summary|||ocr_text format
            parts = summary.split("|||")
            title = parts[0].strip() if len(parts) > 0 else ""
            body = parts[1].strip() if len(parts) > 1 else summary
            ocr_text = parts[2].strip() if len(parts) > 2 else ""

            # Save only the summary text on the record_content entry (no prefixes)
            display_content = body

            db = get_db_client()
            db.table("record_content").update({"content": display_content}).eq("id", record_content.metadata.get("content_id", "")).eq("business_id", record_content.business_id).execute()

            # Update record title if current title is a hash
            if title:
                record = await get_record(record_content.business_id, record_content.record_id)
                if record and (record.get("title", "").startswith("#") or record.get("title") == "Untitled"):
                    await update_record(record_content.business_id, record_content.record_id, title=title)

            # Embed the full structured text (title + summary + OCR content)
            summary = f"Title: {title}\nSummary: {body}\nContent: {ocr_text}" if ocr_text else display_content

            logger.info(f"Updated content with OCR summary for record {record_content.record_id}")

        # For text content, also update record title from first content
        if record_content.content_type == "text":
            from app.db.tools.records import update_record, get_record
            record = await get_record(record_content.business_id, record_content.record_id)
            if record and (record.get("title", "").startswith("#") or record.get("title") == "Untitled"):
                # Use first 60 chars of text as title
                title = record_content.content[:60].strip()
                if title:
                    await update_record(record_content.business_id, record_content.record_id, title=title)

            logger.info(f"Updated content with OCR summary for record {record_content.record_id}")

        embedding_client = get_embedding_client()
        embedding = await embedding_client.aembed_query(summary)

        now = datetime.now(timezone.utc).isoformat()
        entry = KnowledgeEntry(
            knowledge_id=str(uuid4()),
            business_id=record_content.business_id,
            record_id=record_content.record_id,
            content_type=record_content.content_type,
            summary=summary,
            structured_metadata=record_content.metadata,
            embedding=embedding,
            version=1,
            created_at=now,
            updated_at=now,
        )

        store.insert(entry)

        return ProcessingResult(success=True, entry=entry)

    except Exception as e:
        logger.error(f"Failed to process record content for {record_content.record_id}: {e}", exc_info=True)
        return ProcessingResult(success=False, error=str(e))


async def get_record_understanding(business_id: str, record_id: str) -> AIUnderstanding:
    from app.db.tools.record_tools import get_record_knowledge_tools
    from app.db.tools.records import get_record
    from app.db.client import get_client
    from app.lib.agent_executor import execute_task

    config = get_record_knowledge_config()
    agent = _get_insight_agent()
    tools = get_record_knowledge_tools(business_id, record_id)

    description = f"Generate AI understanding for record {record_id} in business {business_id}. Use the tools to search for relevant knowledge."

    try:
        raw = await execute_task(
            agent=agent,
            description=description,
            tools=tools,
            expected_output=agent.expected_output,
            output_pydantic=AIUnderstanding,
            use_system_prompt=True,
           
        )
        data = parse_json_output(raw)
        understanding = AIUnderstanding(**data)

        client = get_client()
        existing = await get_record(business_id, record_id)
        current_insights = (existing or {}).get("ai_insight") or []

        new_entry = {
            "version": len(current_insights) + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "insight": understanding.insight,
            "suggested_questions": understanding.suggested_questions,
        }
        current_insights.append(new_entry)

        client.table("records").update({"ai_insight": current_insights}).eq("id", record_id).eq("business_id", business_id).execute()

        return understanding
    except Exception as e:
        logger.error(f"Understanding generation failed: {e}", exc_info=True)
        return AIUnderstanding(insight=raw[:500] if raw else "Understanding generation failed.")
