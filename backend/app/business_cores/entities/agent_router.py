from __future__ import annotations

from dataclasses import dataclass

from .config.config import EntityConfig
from .config.service import (
    EntityConfigService,
    entity_config_service,
)


@dataclass(frozen=True)
class EntityRoute:
    """Resolved target for an entity extraction run."""

    object_type: str
    agent_name: str
    config: EntityConfig


class EntityAgentRouter:
    """
    Resolves an object_type to the entity specialist that
    should handle it.

    A route only exists when the business has an entity
    configuration for the object_type AND that configuration
    has an enabled agent. Callers treat ``None`` as
    "no specialist configured".
    """

    def __init__(
        self,
        *,
        config_service: EntityConfigService = entity_config_service,
    ) -> None:
        self.config_service = config_service

    async def route(
        self,
        *,
        business_id: str,
        object_type: str,
    ) -> EntityRoute | None:

        object_type = object_type.strip()

        if not object_type:
            return None

        config = await self.config_service.get_or_create(
            business_id=business_id,
            object_type=object_type,
        )

        if config is None:
            return None

        if not config.is_agent_enabled():
            return None

        # is_agent_enabled() guarantees agent is not None.
        assert config.agent is not None

        return EntityRoute(
            object_type=config.object_type,
            agent_name=config.agent.agent_name,
            config=config,
        )

    async def routes(
        self,
        *,
        business_id: str,
    ) -> list[EntityRoute]:

        configs = await self.config_service.list(
            business_id=business_id,
            enabled_only=True,
        )

        return [
            EntityRoute(
                object_type=config.object_type,
                agent_name=config.agent.agent_name,
                config=config,
            )
            for config in configs
            if config.is_agent_enabled()
            and config.agent is not None
        ]


entity_agent_router = EntityAgentRouter()
