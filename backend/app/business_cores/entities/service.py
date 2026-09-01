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

    async def search(
        self,
        *,
        business_id: str,
        object_type: str,
        filters: dict[str, Any],
        limit: int = 20,
    ) -> list[dict[str, Any]]:

        return await self.repository.search(
            business_id=business_id,
            object_type=object_type,
            filters=filters,
            limit=limit,
        )

    async def inspect_database(
        self,
        *,
        business_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:

        return await self.repository.inspect_database(
            business_id=business_id,
            limit=limit,
            offset=offset,
        )

    async def inspect_collection(
        self,
        *,
        business_id: str,
        collection: str,
    ) -> dict[str, Any]:

        return await self.repository.inspect_collection(
            business_id=business_id,
            collection=collection,
        )

    async def inspect_collections(
        self,
        *,
        business_id: str,
        collections: list[str],
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:

        return await self.repository.inspect_collections(
            business_id=business_id,
            collections=collections,
            limit=limit,
            offset=offset,
        )

    async def query_collection(
        self,
        *,
        business_id: str,
        collection: str,
        filters: dict[str, Any],
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:

        return await self.repository.query_collection(
            business_id=business_id,
            collection=collection,
            filters=filters,
            limit=limit,
            offset=offset,
        )

    async def profile_collection(
        self,
        *,
        business_id: str,
        collection: str,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:

        return await self.repository.profile_collection(
            business_id=business_id,
            collection=collection,
            fields=fields,
        )

    async def search_business_data(
        self,
        *,
        business_id: str,
        collection: str,
        query: str,
        search_type: str,
        fields: list[str],
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:

        return await self.repository.search_business_data(
            business_id=business_id,
            collection=collection,
            query=query,
            search_type=search_type,
            fields=fields,
            limit=limit,
            offset=offset,
        )

    async def discover_relationships(
        self,
        *,
        business_id: str,
        collections: list[str] | None = None,
    ) -> list[dict[str, Any]]:

        return await self.repository.discover_relationships(
            business_id=business_id,
            collections=collections,
        )

    async def find_collections_path(
        self,
        *,
        business_id: str,
        from_collection: str,
        to_collection: str,
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:

        return await self.repository.find_collections_path(
            business_id=business_id,
            from_collection=from_collection,
            to_collection=to_collection,
            max_depth=max_depth,
        )

    async def aggregate_collection(
        self,
        *,
        business_id: str,
        collection: str,
        filters: dict[str, Any],
        group_by: list[str],
        metrics: list[dict[str, str]],
    ) -> list[dict[str, Any]]:

        return await self.repository.aggregate_collection(
            business_id=business_id,
            collection=collection,
            filters=filters,
            group_by=group_by,
            metrics=metrics,
        )

    async def aggregate_related_data(
        self,
        *,
        business_id: str,
        collections: list[str],
        relationship: dict[str, str],
        filters: dict[str, Any],
        group_by: list[str],
        metrics: list[dict[str, str]],
    ) -> list[dict[str, Any]]:

        return await self.repository.aggregate_related_data(
            business_id=business_id,
            collections=collections,
            relationship=relationship,
            filters=filters,
            group_by=group_by,
            metrics=metrics,
        )

    async def traverse_relationships(
        self,
        *,
        business_id: str,
        start_collection: str,
        relationships: list[dict[str, str]],
        filters: dict[str, Any],
        fields: list[str],
        limit: int = 20,
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:

        return await self.repository.traverse_relationships(
            business_id=business_id,
            start_collection=start_collection,
            relationships=relationships,
            filters=filters,
            fields=fields,
            limit=limit,
            max_depth=max_depth,
        )


entity_service = EntityService(
    registry=entity_registry,
    config_service=entity_config_service,
    repository=entity_registry.repository,
)
