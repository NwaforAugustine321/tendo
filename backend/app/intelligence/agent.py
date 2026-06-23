"""Business Intelligence Agent — main reasoning loop."""

import json
import logging

from app.events.models import BusinessEvent, Job
from app.intelligence.config import get_intelligence_config
from app.intelligence.models import AgentError, AgentStatus, KnowledgeChangeSet
from app.db.graph_client import get_graph_client
from app.intelligence.persistence import PersistenceLayer
from app.intelligence.tools import INTELLIGENCE_TOOLS
from app.llm.specs import load

logger = logging.getLogger(__name__)


async def process_events(job: Job, events: list[BusinessEvent]) -> None:
    """Main entry point: analyze events, reason with tools, persist knowledge."""
    config = get_intelligence_config()

    # Load system prompt from agent spec files
    agent_config = load("bla", tools=INTELLIGENCE_TOOLS)

    # Get LLM
    from app.llm.client import get_client as get_llm

    llm = get_llm()

    # Bind tools
    llm_with_tools = llm.bind_tools(INTELLIGENCE_TOOLS)

    # Build prompt with events
    events_summary = json.dumps(
        [
            {
                "event_type": e.event_type,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "source": e.source,
                "payload": e.payload,
                "metadata": e.metadata,
            }
            for e in events
        ],
        default=str,
    )

    prompt = [
        {"role": "system", "content": agent_config.system_prompt},
        {
            "role": "user",
            "content": f"Process these business events for business_id={job.stream_key.split(':')[0]}:\n\n{events_summary}",
        },
    ]

    # Reasoning loop with tool calls
    max_iterations = config.max_iterations
    raw = ""

    for iteration in range(max_iterations):
        response = await llm_with_tools.ainvoke(prompt)

        # If LLM wants to call tools
        if response.tool_calls:
            logger.info(
                f"BLA iteration {iteration}: calling {len(response.tool_calls)} tools"
            )
            prompt.append(
                {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": response.tool_calls,
                }
            )

            # Execute tools
            for tc in response.tool_calls:
                tool_map = {t.name: t for t in INTELLIGENCE_TOOLS}
                tool_fn = tool_map.get(tc["name"])
                if tool_fn:
                    try:
                        result = await tool_fn.ainvoke(tc["args"])
                    except Exception as e:
                        result = f"Tool error: {e}"
                else:
                    result = f"Unknown tool: {tc['name']}"

                prompt.append(
                    {"role": "tool", "tool_call_id": tc["id"], "content": str(result)}
                )
            continue

        # No tool calls — LLM is ready to produce output
        raw = response.content.strip() if response.content else ""
        break
    else:
        raise AgentError(
            f"Max iterations ({max_iterations}) exceeded", iteration=max_iterations
        )

    # Parse the KnowledgeChangeSet
    logger.info(f"BLA raw output: {raw[:300]}")
    change_set = _parse_change_set(raw, job)

    # Handle status-based flow
    if change_set.status == AgentStatus.NO_CHANGES:
        logger.info("BLA: no changes detected")
        return

    if change_set.status == AgentStatus.NEEDS_RETRIEVAL:
        logger.info(f"BLA: needs retrieval — {len(change_set.tool_requests)} requests")
        # Tool requests are handled during the reasoning loop above;
        # if we reach here, the agent could not resolve within max_iterations
        return

    # Persist (status == completed)
    graph = get_graph_client()
    persistence = PersistenceLayer(graph)
    result = await persistence.persist(change_set)

    logger.info(
        f"BLA persisted: {result.operations_applied} ops, {result.nodes_created} nodes created"
    )


def _parse_change_set(raw: str, job: Job) -> KnowledgeChangeSet:
    """Parse LLM output into a validated KnowledgeChangeSet."""
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        start = clean.find("{")
        if start != -1:
            depth = 0
            for i in range(start, len(clean)):
                if clean[i] == "{":
                    depth += 1
                elif clean[i] == "}":
                    depth -= 1
                if depth == 0:
                    clean = clean[start : i + 1]
                    break

        data = json.loads(clean)
        data["business_id"] = job.stream_key.split(":")[0]
        data["job_id"] = str(job.id)
        return KnowledgeChangeSet(**data)
    except Exception as e:
        logger.warning(f"BLA: failed to parse change set: {e}")
        return KnowledgeChangeSet(
            business_id=job.stream_key.split(":")[0],
            job_id=str(job.id),
            operations=[],
            reasoning_summary=raw[:500],
            status=AgentStatus.NO_CHANGES,
        )
