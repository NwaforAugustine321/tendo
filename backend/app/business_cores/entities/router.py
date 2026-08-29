from __future__ import annotations

import json
from typing import Any

from app.runtime.agents.agent import Agent
from app.runtime.llm_vendors.langchain import LangChainLLM
from app.runtime.utils.tag_parser import extract_json, extract_tag

from .agent import EntityAgent
from .agent_router import (
    EntityAgentRouter,
    entity_agent_router,
)
from .config.service import (
    EntityConfigService,
    entity_config_service,
)
from .types import EntityResolution


class EntityOrchestrator:

    def __init__(
        self,
        *,
        llm: LangChainLLM,
        router: EntityAgentRouter = entity_agent_router,
        config_service: EntityConfigService = entity_config_service,
    ) -> None:
        self.llm = llm
        self.router = router
        self.config_service = config_service

    async def run(
        self,
        *,
        business_id: str,
        source: str,
    ) -> list[EntityResolution]:

        # Get all entity configurations available
        # for this business.
        configs = await self.config_service.list(
            business_id=business_id,
            enabled_only=True,
        )

        if not configs:
            return []

        configured_types = {
            config.object_type
            for config in configs
            if config.agent is not None
            and config.agent.enabled
        }

        if not configured_types:
            return []

        # Ask the main agent which entities are present
        # in the source.
        entity_types = await self._find_entity_types(
            source=source,
            entity_types=configured_types,
        )

        results: list[EntityResolution] = []

        for object_type in entity_types:

            route = await self.router.route(
                business_id=business_id,
                object_type=object_type,
            )

            if route is None:
                raise ValueError(
                    f"No enabled entity agent configured for "
                    f"{object_type}"
                )

            entity_agent = EntityAgent(
                config=route.config,
                router=self.router,
                llm=self.llm,
            )

            result = await entity_agent.run(
                business_id=business_id,
                object_type=object_type,
                source=source,
            )

            results.append(result)

        return results

    async def _find_entity_types(
        self,
        *,
        source: str,
        entity_types: set[str],
    ) -> list[str]:

        available_types = sorted(entity_types)

        prompt = f"""
Determine which entity types are present in the source.

Available entity types:
{json.dumps(available_types, indent=2)}

Rules:
- Only return entity types from the available list.
- Do not invent entity types.
- Select every entity type that has enough information
  in the source to extract.
- Return an empty list if none are present.
- Return exactly one <entities> tag.
- The content inside <entities> must be a valid JSON array.
- Do not return markdown or explanations.

Required response format:

<entities>
["customer", "transaction"]
</entities>

Source:
{source}
""".strip()

        agent = Agent(
            name="Entity Orchestrator",
            llm=self.llm,
            instructions=prompt,
            enable_runtime_mem=False,
            enable_runtime_rag=False,
            enable_self_reflection=False,
        )

        session = agent.create_session()

        response = await session.run(
            source,
        )

        selected = self._parse_entity_types(
            response.text,
        )

        # IMPORTANT:
        # The LLM is never trusted to introduce a new
        # entity type.
        invalid = set(selected) - entity_types

        if invalid:
            raise ValueError(
                "Entity orchestrator returned unsupported "
                f"entity types: {', '.join(sorted(invalid))}"
            )

        # Remove duplicates while preserving order.
        result: list[str] = []
        seen: set[str] = set()

        for object_type in selected:
            if object_type in seen:
                continue

            seen.add(object_type)
            result.append(object_type)

        return result

    @staticmethod
    def _parse_entity_types(
        text: str,
    ) -> list[str]:

        raw = extract_tag(
            text,
            "entities",
        )

        if not raw:
            raise ValueError(
                "Entity orchestrator response does not "
                "contain <entities> tag"
            )

        parsed = extract_json(
            raw,
        )

        if not isinstance(parsed, list):
            raise ValueError(
                "Entity orchestrator <entities> tag must "
                "contain a JSON array"
            )

        result: list[str] = []

        for value in parsed:

            if not isinstance(value, str):
                raise ValueError(
                    "Entity type must be a string"
                )

            value = value.strip()

            if value:
                result.append(value)

        return result
