import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel

from app.embeddings.client import get_embedding_client
from app.lib.json_parser import parse_json_output
from app.record_knowledge.config import get_record_knowledge_config
from app.record_knowledge.models import RecordContentInput, KnowledgeEntry, ProcessingResult, AIUnderstanding
from app.record_knowledge import store

logger = logging.getLogger(__name__)


class SummaryOutput(BaseModel):
    summary: str


_summarizer_agent = None
_insight_agent = None


def _get_summarizer_agent():
    global _summarizer_agent
    if _summarizer_agent is None:
        from app.agents.models import Agent
        _summarizer_agent = Agent.from_spec("text_summarizer")
    return _summarizer_agent


def _get_insight_agent():
    global _insight_agent
    if _insight_agent is None:
        from app.agents.models import Agent
        _insight_agent = Agent.from_spec("record_insight")
    return _insight_agent


async def _summarize_text(content: str) -> str:
    from app.lib.agent_executor import execute_task
    from app.lib.context_handler import handle_text_context_length

    config = get_record_knowledge_config()
    max_length = config.max_summary_length

    if not content or not content.strip():
        return "Empty note with no content."

    if len(content.strip()) <= 100:
        return content.strip()

    fitted_content = await handle_text_context_length(content)

    agent = _get_summarizer_agent()

    raw = await execute_task(
        agent=agent,
        description=fitted_content,
        tools=[],
        expected_output=agent.expected_output,
        output_pydantic=SummaryOutput,
        use_system_prompt=True,
        max_iter=1,
    )

    try:
        data = parse_json_output(raw)
        summary = data.get("summary", raw.strip())
    except Exception:
        summary = raw.strip() if raw else content[:max_length]

    return summary[:max_length]


_SUMMARIZERS = {
    "text": _summarize_text,
}


async def process_record_content(record_content: RecordContentInput) -> ProcessingResult:
    summarizer = _SUMMARIZERS.get(record_content.content_type)
    if summarizer is None:
        logger.warning(f"Unsupported content_type: {record_content.content_type}")
        return ProcessingResult(success=False, error=f"Unsupported content_type: {record_content.content_type}")

    try:
        summary = await summarizer(record_content.content)

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
            max_iter=config.max_retries + 2,
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
