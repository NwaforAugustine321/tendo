import json
import logging

from app.agents.models import Agent
from app.events.models import BusinessEvent, Job
from app.business_knowledge.config import get_intelligence_config
from app.business_knowledge.models import AgentStatus, InsightOutput
from app.business_knowledge.persistence import InsightPersistence
from app.business_knowledge.tools import INTELLIGENCE_TOOLS

logger = logging.getLogger(__name__)

_bla_agent = Agent.from_spec("bla")


async def process_events(job: Job, events: list[BusinessEvent]) -> None:
    from app.lib.agent_executor import execute_task

    config = get_intelligence_config()
    business_id = job.business_id

    events_summary = json.dumps(
        [
            {
                "event_type": e.event_type,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "source": e.source,
                **(e.payload or {}),
                **(e.metadata or {}),
            }
            for e in events
        ],
        default=str,
    )

    description = (
        f"Process these business events and operations and records for business_id={business_id}:\n\n"
        f"{events_summary}"
    )

    context = f"business_id: {business_id}\njob_id: {job.id}"

    raw = await execute_task(
        agent=_bla_agent,
        description=description,
        tools=INTELLIGENCE_TOOLS,
        expected_output=_bla_agent.expected_output,
        context=context,
        output_pydantic=InsightOutput,
        use_system_prompt=True,
        max_iter=config.max_iterations,
    )

    logger.info(f"BLA raw output: {raw}")

    insight_output = _parse_insight_output(raw, job)

    if insight_output.status == AgentStatus.NO_CHANGES:
        logger.info("BLA: no changes detected")
        return

    if insight_output.status == AgentStatus.NEEDS_RETRIEVAL:
        logger.info("BLA: needs retrieval")
        return

    persistence = InsightPersistence(business_id)
    count = await persistence.persist(insight_output)
    logger.info(f"BLA persisted: {count} insights stored")


def _parse_insight_output(raw: str, job: Job) -> InsightOutput:
    try:
        from app.lib.json_parser import parse_json_output

        data = parse_json_output(raw)
        data["business_id"] = job.business_id
        data["job_id"] = str(job.id)
        return InsightOutput(**data)
    except Exception as e:
        logger.warning(f"BLA: failed to parse insight output: {e}")
        return InsightOutput(
            business_id=job.business_id,
            job_id=str(job.id),
            insights=[],
            reasoning_summary=raw[:500],
            status=AgentStatus.NO_CHANGES,
        )
