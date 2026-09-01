
from __future__ import annotations

from typing import Any

from ..defaults import DEFAULT_ENTITY_CONFIGS
from .config import EntityConfig
from .repository import EntityConfigRepository


class EntityConfigService:

    def __init__(
        self,
        *,
        repository: EntityConfigRepository | None = None,
    ) -> None:
        self.repository = (
            repository
            if repository is not None
            else EntityConfigRepository()
        )

    async def get(
        self,
        *,
        business_id: str,
        object_type: str,
    ) -> EntityConfig | None:

        config = await self.repository.get(
            business_id=business_id,
            object_type=object_type,
        )

        if config is not None:
            return config

        return DEFAULT_ENTITY_CONFIGS.get(
            object_type,
        )

    async def get_or_create(
        self,
        *,
        business_id: str,
        object_type: str,
    ) -> EntityConfig | None:

        config = await self.repository.get(
            business_id=business_id,
            object_type=object_type,
        )

        if config is not None:
            return config

        default_config = DEFAULT_ENTITY_CONFIGS.get(
            object_type,
        )

        if default_config is None:
            return None

        return await self.repository.upsert(
            business_id=business_id,
            config=default_config,
        )

    async def require(
        self,
        *,
        business_id: str,
        object_type: str,
    ) -> EntityConfig:

        config = await self.get_or_create(
            business_id=business_id,
            object_type=object_type,
        )

        if config is None:
            raise ValueError(
                f"Entity configuration not found: "
                f"{object_type}"
            )

        if not config.enabled:
            raise ValueError(
                f"Entity is disabled: {object_type}"
            )

        return config

    async def save(
        self,
        *,
        business_id: str,
        config: EntityConfig,
    ) -> EntityConfig:

        object_type = config.object_type.strip()

        if not object_type:
            raise ValueError(
                "Entity object_type cannot be empty"
            )

        if not config.fields:
            raise ValueError(
                f"Entity must define at least one field: "
                f"{object_type}"
            )

        self._validate_fields(config)

        return await self.repository.upsert(
            business_id=business_id,
            config=config,
        )

    async def delete(
        self,
        *,
        business_id: str,
        object_type: str,
    ) -> bool:

        return await self.repository.delete(
            business_id=business_id,
            object_type=object_type,
        )

    async def list(
        self,
        *,
        business_id: str,
        enabled_only: bool = False,
    ) -> list[EntityConfig]:

        configs = await self.repository.list(
            business_id=business_id,
            enabled_only=enabled_only,
        )

        configured_types = {
            config.object_type
            for config in configs
        }

        defaults = [
            config
            for object_type, config
            in DEFAULT_ENTITY_CONFIGS.items()
            if object_type not in configured_types
            and (
                not enabled_only
                or config.enabled
            )
        ]

        return [
            *configs,
            *defaults,
        ]

    async def list_object_types(
        self,
        *,
        business_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:

        limit = max(
            1,
            min(limit, 100),
        )

        offset = max(
            0,
            offset,
        )

        objects = await self.repository.list_object_types(
            business_id=business_id,
            limit=limit,
            offset=offset,
        )

        return objects

    @staticmethod
    def _validate_fields(
        config: EntityConfig,
    ) -> None:

        field_names: set[str] = set()

        for field_config in config.fields:

            name = field_config.name.strip()

            if not name:
                raise ValueError(
                    f"Entity field name cannot be empty: "
                    f"{config.object_type}"
                )

            if name != field_config.name:
                raise ValueError(
                    f"Entity field name cannot contain "
                    f"leading or trailing whitespace: "
                    f"{config.object_type}.{field_config.name}"
                )

            if name in field_names:
                raise ValueError(
                    f"Duplicate entity field: "
                    f"{config.object_type}.{name}"
                )

            field_names.add(name)

            field_type = field_config.type.strip()

            if not field_type:
                raise ValueError(
                    f"Entity field type cannot be empty: "
                    f"{config.object_type}.{name}"
                )

        if (
            config.agent is not None
            and not config.agent.agent_name.strip()
        ):
            raise ValueError(
                f"Entity agent name cannot be empty: "
                f"{config.object_type}"
            )


entity_config_service = EntityConfigService()
