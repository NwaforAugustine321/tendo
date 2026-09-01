from __future__ import annotations

from typing import Any

from pymongo import ASCENDING
from pymongo.asynchronous.database import AsyncDatabase

from app.db.mongo_client import get_client

from .config import (
    EntityAgentConfig,
    EntityConfig,
    EntityFieldConfig,
)


class EntityConfigRepository:

    collection_name = "entity_configs"

    def __init__(
        self,
        *,
        db: AsyncDatabase | None = None,
    ) -> None:
        self.db = db or get_client()

    @property
    def collection(self):
        return self.db[self.collection_name]

    async def get(
        self,
        *,
        business_id: str,
        object_type: str,
    ) -> EntityConfig | None:

        document = await self.collection.find_one(
            {
                "business_id": business_id,
                "object_type": object_type,
            }
        )

        if document is None:
            return None

        return self._from_document(document)

    async def upsert(
        self,
        *,
        business_id: str,
        config: EntityConfig,
    ) -> EntityConfig:

        document = self._to_document(
            business_id=business_id,
            config=config,
        )

        await self.collection.replace_one(
            {
                "business_id": business_id,
                "object_type": config.object_type,
            },
            document,
            upsert=True,
        )

        return config

    async def delete(
        self,
        *,
        business_id: str,
        object_type: str,
    ) -> bool:

        result = await self.collection.delete_one(
            {
                "business_id": business_id,
                "object_type": object_type,
            }
        )

        return result.deleted_count > 0

    async def list(
        self,
        *,
        business_id: str,
        enabled_only: bool = False,
    ) -> list[EntityConfig]:

        query: dict[str, Any] = {
            "business_id": business_id,
        }

        if enabled_only:
            query["enabled"] = True

        cursor = (
            self.collection
            .find(query)
            .sort("object_type", ASCENDING)
        )

        documents = await cursor.to_list(
            length=None,
        )

        return [
            self._from_document(document)
            for document in documents
        ]

    async def list_object_types(
        self,
        *,
        business_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:

        if not business_id:
            raise ValueError(
                "business_id cannot be empty"
            )

        limit = max(
            1,
            min(limit, 100),
        )

        offset = max(
            0,
            offset,
        )

        cursor = (
            self.collection
            .find(
                {
                    "business_id": business_id,
                    "enabled": True,
                },
                {
                    "_id": 0,
                    "object_type": 1,
                    "fields.name": 1,
                },
            )
            .sort(
                "object_type",
                ASCENDING,
            )
            .skip(offset)
            .limit(limit)
        )

        documents = await cursor.to_list(
            length=limit,
        )

        return [
            {
                "object_type": document["object_type"],
                "fields": [
                    field["name"]
                    for field in document.get(
                        "fields",
                        [],
                    )
                    if field.get("name")
                ],
            }
            for document in documents
        ]

    async def ensure_indexes(self) -> None:

        await self.collection.create_index(
            [
                ("business_id", ASCENDING),
                ("object_type", ASCENDING),
            ],
            unique=True,
            name="business_object_type",
        )

        await self.collection.create_index(
            [
                ("business_id", ASCENDING),
                ("enabled", ASCENDING),
                ("object_type", ASCENDING),
            ],
            name="business_enabled_object_type",
        )

    @staticmethod
    def _to_document(
        *,
        business_id: str,
        config: EntityConfig,
    ) -> dict[str, Any]:

        return {
            "business_id": business_id,
            "object_type": config.object_type,
            "enabled": config.enabled,
            "fields": [
                {
                    "name": field_config.name,
                    "type": field_config.type,
                    "required": field_config.required,
                    "identity": field_config.identity,
                    "description": field_config.description,
                    "aliases": list(
                        field_config.aliases
                    ),
                    "config": field_config.config,
                }
                for field_config in config.fields
            ],
            "agent": (
                {
                    "agent_name": config.agent.agent_name,
                    "enabled": config.agent.enabled,
                    "instructions": config.agent.instructions,
                    "config": config.agent.config,
                }
                if config.agent is not None
                else None
            ),
            "config": config.config,
        }

    @staticmethod
    def _from_document(
        document: dict[str, Any],
    ) -> EntityConfig:

        fields = tuple(
            EntityFieldConfig(
                name=field["name"],
                type=field.get(
                    "type",
                    "string",
                ),
                required=field.get(
                    "required",
                    False,
                ),
                identity=field.get(
                    "identity",
                    False,
                ),
                description=field.get(
                    "description",
                    "",
                ),
                aliases=tuple(
                    field.get(
                        "aliases",
                        [],
                    )
                ),
                config=field.get(
                    "config",
                    {},
                ),
            )
            for field in document.get(
                "fields",
                [],
            )
        )

        agent_data = document.get("agent")

        agent = (
            EntityAgentConfig(
                agent_name=agent_data["agent_name"],
                enabled=agent_data.get(
                    "enabled",
                    True,
                ),
                instructions=agent_data.get(
                    "instructions",
                    "",
                ),
                config=agent_data.get(
                    "config",
                    {},
                ),
            )
            if agent_data is not None
            else None
        )

        return EntityConfig(
            object_type=document["object_type"],
            enabled=document.get(
                "enabled",
                True,
            ),
            fields=fields,
            agent=agent,
            config=document.get(
                "config",
                {},
            ),
        )
