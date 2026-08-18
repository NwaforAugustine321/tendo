# """Business Snapshot Agent — generates narrative snapshots from business knowledge."""

# from __future__ import annotations

# import json
# import logging

# from app.agents.models import Agent
# from app.business_snapshot.config import get_snapshot_config
# from app.business_snapshot.models import BusinessSnapshot, SnapshotRecommendation, SnapshotStory
# from app.db.tools.snapshot import save_snapshot as db_save_snapshot
# from app.lib.json_parser import parse_json_output
# from app.memory.tools import get_knowledge_tools

# logger = logging.getLogger(__name__)

# _snapshot_agent = Agent.from_spec("snapshot")


# async def generate_snapshot(business_id: str) -> BusinessSnapshot:
#     from app.llm.client import get_client

#     config = get_snapshot_config()

#     description = (
#         f"Generate a business snapshot for business_id={business_id}.\n\n"
#     )

#     context = f"business_id: {business_id}"

#     llm = get_client()
#     response = await llm.ainvoke([
#         {"role": "system", "content": _snapshot_agent.backstory or ""},
#         {"role": "user", "content": description},
#     ])
#     raw = response.content.strip() if response.content else ""

#     logger.info(f"Snapshot agent output: {raw[:200]}")
#     snapshot = _parse_snapshot_output(raw, business_id)

#     db_save_snapshot({
#         "business_id": snapshot.business_id,
#         "stories": [s.model_dump() for s in snapshot.stories],
#         "recommendations": [r.model_dump() for r in snapshot.recommendations],
#     })


# def _parse_snapshot_output(raw_output: str, business_id: str) -> BusinessSnapshot:
#     """Parse agent output into a BusinessSnapshot model."""
#     if not raw_output:
#         return BusinessSnapshot(business_id=business_id, stories=[], recommendations=[])

#     try:
#         data = parse_json_output(raw_output)
#         stories = [SnapshotStory(**s) for s in data.get("stories", [])]
#         recommendations = [SnapshotRecommendation(**r) for r in data.get("recommendations", [])]
#         return BusinessSnapshot(
#             business_id=business_id,
#             stories=stories,
#             recommendations=recommendations,
#         )
#     except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
#         logger.warning(f"Failed to parse snapshot output for {business_id}: {e}")
#         return BusinessSnapshot(business_id=business_id, stories=[], recommendations=[])
