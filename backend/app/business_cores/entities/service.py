from __future__ import annotations

from typing import Any

from .config.service import (
    EntityConfigService,
    entity_config_service,
)
from .identity import build_identity_strategy
from .registry import EntityRegistry, entity_registry
from .repository import EntityRepository
from .types import EntityInput, EntityResolution


class EntityService:

    def __init__(
        self,
        *,
        registry: EntityRegistry,
        config_service: EntityConfigService,
        repository: EntityRepository,
    ) -> None:
        self.registry = registry
        self.config_service = config_service
        self.repository = repository

    async def resolve(
        self,
        *,
        business_id: str,
        entity: EntityInput,
    ) -> EntityResolution:

        config = await self.config_service.require(
            business_id=business_id,
            object_type=entity.object_type,
        )

        config.validate_data(entity.data)

        data = config.filter_data(
            entity.data,
        )

        identity_strategy = build_identity_strategy(
            config,
        )

        identities = identity_strategy.build_identities(
            business_id=business_id,
            data=data,
        )

        if self.registry.has(entity.object_type):
            service = self.registry.get(
                entity.object_type,
            )

            result = await service.resolve(
                business_id=business_id,
                data=data,
            )

        else:
            result = await self.repository.resolve(
                business_id=business_id,
                object_type=entity.object_type,
                data=data,
                identities=identities,
            )

        return EntityResolution(
            object_type=entity.object_type,
            object_id=(
                result.object_id
                if hasattr(result, "object_id")
                else str(result["id"])
            ),
            created=(
                result.created
                if hasattr(result, "created")
                else bool(result["created"])
            ),
            status=(
                result.status
                if hasattr(result, "status")
                else result.get("status", "active")
            ),
        )

    async def update(
        self,
        *,
        business_id: str,
        object_id: str,
        entity: EntityInput,
    ) -> EntityResolution:

        config = await self.config_service.require(
            business_id=business_id,
            object_type=entity.object_type,
        )

        config.validate_data(entity.data)

        data = config.filter_data(
            entity.data,
        )

        if self.registry.has(entity.object_type):
            service = self.registry.get(
                entity.object_type,
            )

            result = await service.update(
                business_id=business_id,
                object_id=object_id,
                data=data,
            )

        else:
            identity_strategy = build_identity_strategy(
                config,
            )

            identities = identity_strategy.build_identities(
                business_id=business_id,
                data=data,
            )

            result = await self.repository.update(
                business_id=business_id,
                object_type=entity.object_type,
                object_id=object_id,
                data=data,
                identities=identities,
            )

        return EntityResolution(
            object_type=entity.object_type,
            object_id=(
                result.object_id
                if hasattr(result, "object_id")
                else str(result["id"])
            ),
            created=False,
            status=(
                result.status
                if hasattr(result, "status")
                else result.get("status", "active")
            ),
        )

    async def get(
        self,
        *,
        business_id: str,
        object_type: str,
        object_id: str,
    ) -> dict[str, Any] | None:

        await self.config_service.require(
            business_id=business_id,
            object_type=object_type,
        )

        if self.registry.has(object_type):
            service = self.registry.get(
                object_type,
            )

            return await service.get(
                business_id=business_id,
                object_id=object_id,
            )

        return await self.repository.get(
            business_id=business_id,
            object_type=object_type,
            object_id=object_id,
        )

    async def delete(
        self,
        *,
        business_id: str,
        object_type: str,
        object_id: str,
    ) -> bool:

        await self.config_service.require(
            business_id=business_id,
            object_type=object_type,
        )

        if self.registry.has(object_type):
            service = self.registry.get(
                object_type,
            )

            return await service.delete(
                business_id=business_id,
                object_id=object_id,
            )

        return await self.repository.delete(
            business_id=business_id,
            object_type=object_type,
            object_id=object_id,
        )

    async def list(
        self,
        *,
        business_id: str,
        object_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:

        await self.config_service.require(
            business_id=business_id,
            object_type=object_type,
        )

        if self.registry.has(object_type):
            service = self.registry.get(
                object_type,
            )

            return await service.list(
                business_id=business_id,
                limit=limit,
                offset=offset,
            )

        return await self.repository.list(
            business_id=business_id,
            object_type=object_type,
            limit=limit,
            offset=offset,
        )


entity_service = EntityService(
    registry=entity_registry,
    config_service=entity_config_service,
    repository=entity_registry.repository,
)
