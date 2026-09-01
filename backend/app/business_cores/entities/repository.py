from __future__ import annotations

import re
from typing import Any

from app.db.mongo_client import get_client

from ..core.identity import Identity
from ..core.repository import BusinessObjectRepository
from pymongo import ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase

SUPPORTED_AGGREGATION_OPERATIONS = (
    "count",
    "sum",
    "average",
    "min",
    "max",
    "median",
    "distinct",
    "standard_deviation",
    "percentile",
)

SUPPORTED_SEARCH_TYPES = (
    "exact",
    "phrase",
    "contains",
    "regex",
)


class EntityRepository(BusinessObjectRepository):
    """Repository for generic business entities."""

    TABLE = "business_entities"

    def __init__(self) -> None:
        self._db: AsyncDatabase = get_client()

    async def resolve(
        self,
        *,
        business_id: str,
        object_type: str,
        data: dict[str, Any],
        identities: list[Identity],
    ) -> dict[str, Any]:

        collection = self._db[self.TABLE]

        for identity in identities:
            row = await collection.find_one(
                {
                    "business_id": business_id,
                    "object_type": object_type,
                    f"data.{identity.field}": identity.value,
                }
            )

            if row:
                return {
                    "id": str(row["_id"]),
                    "created": False,
                    "status": row.get("status", "active"),
                }

        payload = {
            "business_id": business_id,
            "object_type": object_type,
            "data": data,
            "status": "active",
        }

        result = await collection.insert_one(payload)

        return {
            "id": str(result.inserted_id),
            "created": True,
            "status": "active",
        }

    async def update(
        self,
        *,
        business_id: str,
        object_type: str,
        object_id: str,
        data: dict[str, Any],
        identities: list[Identity],
    ) -> dict[str, Any]:
        from bson import ObjectId

        collection = self._db[self.TABLE]

        result = await collection.find_one_and_update(
            {
                "_id": ObjectId(object_id),
                "business_id": business_id,
                "object_type": object_type,
            },
            {
                "$set": {
                    "data": data,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

        if not result:
            return {}

        return {
            "id": str(result["_id"]),
            "created": False,
            "status": result.get("status", "active"),
        }

    async def get(
        self,
        *,
        business_id: str,
        object_type: str,
        object_id: str,
    ) -> dict[str, Any] | None:
        from bson import ObjectId

        collection = self._db[self.TABLE]

        result = await collection.find_one(
            {
                "_id": ObjectId(object_id),
                "business_id": business_id,
                "object_type": object_type,
            }
        )

        if not result:
            return None

        result["id"] = str(result.pop("_id"))

        return result

    async def delete(
        self,
        *,
        business_id: str,
        object_type: str,
        object_id: str,
    ) -> bool:
        from bson import ObjectId

        collection = self._db[self.TABLE]

        result = await collection.delete_one(
            {
                "_id": ObjectId(object_id),
                "business_id": business_id,
                "object_type": object_type,
            }
        )

        return result.deleted_count > 0

    async def list(
        self,
        *,
        business_id: str,
        object_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        collection = self._db[self.TABLE]

        cursor = (
            collection.find(
                {
                    "business_id": business_id,
                    "object_type": object_type,
                }
            )
            .skip(offset)
            .limit(limit)
        )

        rows = await cursor.to_list(length=limit)

        return [
            self._normalize_document(row)
            for row in rows
        ]

    async def search(
        self,
        *,
        business_id: str,
        object_type: str,
        filters: dict[str, Any],
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        collection = self._db[self.TABLE]

        _filter = {
            "business_id": business_id,
            "object_type": object_type,
        }

        _filter.update(
            self._build_data_filters(filters)
        )

        cursor = collection.find(
            _filter
        ).limit(limit)

        rows = await cursor.to_list(length=limit)

        return [
            self._normalize_document(row)
            for row in rows
        ]

    async def inspect_database(
        self,
        *,
        business_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        collection = self._db[self.TABLE]

        pipeline = [
            {
                "$match": {
                    "business_id": business_id,
                }
            },
            {
                "$group": {
                    "_id": "$object_type",
                }
            },
            {
                "$sort": {
                    "_id": 1,
                }
            },
            {
                "$skip": offset,
            },
            {
                "$limit": limit,
            },
            {
                "$project": {
                    "_id": 0,
                    "collection": "$_id",
                }
            },
        ]

        rows = await collection.aggregate(
            pipeline
        ).to_list(length=limit)

        return rows

    async def inspect_collection(
        self,
        *,
        business_id: str,
        collection: str,
    ) -> dict[str, Any]:
        collection = self._db[self.TABLE]

        pipeline = [
            {
                "$match": {
                    "business_id": business_id,
                    "object_type": collection,
                }
            },
            {
                "$facet": {
                    "count": [
                        {
                            "$count": "value",
                        }
                    ],
                    "sample": [
                        {
                            "$limit": 100,
                        },
                        {
                            "$project": {
                                "_id": 0,
                                "data": 1,
                            }
                        },
                    ],
                }
            },
        ]

        result = await collection.aggregate(
            pipeline
        ).to_list(length=1)

        if not result:
            return {
                "collection": collection,
                "fields": [],
                "record_count": 0,
            }

        result = result[0]

        count_rows = result.get("count", [])
        record_count = (
            count_rows[0]["value"]
            if count_rows
            else 0
        )

        field_pipeline = [
            {
                "$match": {
                    "business_id": business_id,
                    "object_type": collection,
                }
            },
            {
                "$project": {
                    "fields": {
                        "$objectToArray": {
                            "$ifNull": [
                                "$data",
                                {},
                            ]
                        }
                    }
                }
            },
            {
                "$unwind": "$fields",
            },
            {
                "$group": {
                    "_id": "$fields.k",
                    "types": {
                        "$addToSet": {
                            "$type": "$fields.v",
                        }
                    },
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "name": "$_id",
                    "types": 1,
                }
            },
            {
                "$sort": {
                    "name": 1,
                }
            },
        ]

        fields = await collection.aggregate(
            field_pipeline
        ).to_list(length=None)

        normalized_fields = []

        for field in fields:
            types = field.get("types", [])

            normalized_fields.append(
                {
                    "name": field["name"],
                    "type": (
                        types[0]
                        if len(types) == 1
                        else "mixed"
                    ),
                    "types": types,
                }
            )

        return {
            "collection": collection,
            "record_count": record_count,
            "fields": normalized_fields,
        }

    async def inspect_collections(
        self,
        *,
        business_id: str,
        collections: list[str],
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        collection = self._db[self.TABLE]

        selected = collections[
            offset: offset + limit
        ]

        if not selected:
            return []

        pipeline = [
            {
                "$match": {
                    "business_id": business_id,
                    "object_type": {
                        "$in": selected,
                    },
                }
            },
            {
                "$project": {
                    "object_type": 1,
                    "data": 1,
                }
            },
            {
                "$facet": {
                    "counts": [
                        {
                            "$group": {
                                "_id": "$object_type",
                                "record_count": {
                                    "$sum": 1,
                                },
                            }
                        }
                    ],
                    "fields": [
                        {
                            "$project": {
                                "object_type": 1,
                                "fields": {
                                    "$objectToArray": {
                                        "$ifNull": [
                                            "$data",
                                            {},
                                        ]
                                    }
                                },
                            }
                        },
                        {
                            "$unwind": "$fields",
                        },
                        {
                            "$group": {
                                "_id": {
                                    "collection": "$object_type",
                                    "field": "$fields.k",
                                },
                                "types": {
                                    "$addToSet": {
                                        "$type": "$fields.v",
                                    }
                                },
                            }
                        },
                    ],
                }
            },
        ]

        result = await collection.aggregate(
            pipeline
        ).to_list(length=1)

        if not result:
            return []

        result = result[0]

        counts = {
            row["_id"]: row["record_count"]
            for row in result.get("counts", [])
        }

        fields_bycollection: dict[
            str,
            list[dict[str, Any]],
        ] = {}

        for row in result.get("fields", []):
            collection_name = row["_id"]["collection"]
            field_name = row["_id"]["field"]
            types = row.get("types", [])

            fields_bycollection.setdefault(
                collection_name,
                [],
            ).append(
                {
                    "name": field_name,
                    "type": (
                        types[0]
                        if len(types) == 1
                        else "mixed"
                    ),
                    "types": types,
                }
            )

        return [
            {
                "collection": collection_name,
                "record_count": counts.get(
                    collection_name,
                    0,
                ),
                "fields": sorted(
                    fields_bycollection.get(
                        collection_name,
                        [],
                    ),
                    key=lambda item: item["name"],
                ),
            }
            for collection_name in selected
        ]

    async def query_collection(
        self,
        *,
        business_id: str,
        collection: str,
        filters: dict[str, Any],
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:

        collection = self._db[self.TABLE]

        _filter = {
            "business_id": business_id,
            "object_type": collection,
        }

        _filter.update(
            self._build_data_filters(filters)
        )

        cursor = (
            collection.find(_filter)
            .skip(offset)
            .limit(limit)
        )

        rows = await cursor.to_list(length=limit)

        return [
            self._normalize_document(row)
            for row in rows
        ]

    async def profile_collection(
        self,
        *,
        business_id: str,
        collection: str,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:

        collection = self._db[self.TABLE]

        match_stage = {
            "$match": {
                "business_id": business_id,
                "object_type": collection,
            }
        }

        if fields:
            target_fields = fields
        else:
            field_pipeline = [
                match_stage,
                {
                    "$project": {
                        "fields": {
                            "$objectToArray": {
                                "$ifNull": [
                                    "$data",
                                    {},
                                ]
                            }
                        }
                    }
                },
                {
                    "$unwind": "$fields",
                },
                {
                    "$group": {
                        "_id": "$fields.k",
                    }
                },
                {
                    "$sort": {
                        "_id": 1,
                    }
                },
            ]

            field_rows = await collection.aggregate(
                field_pipeline
            ).to_list(length=None)

            target_fields = [
                row["_id"]
                for row in field_rows
            ]

        if not target_fields:
            count_result = await collection.aggregate(
                [
                    match_stage,
                    {
                        "$count": "record_count",
                    },
                ]
            ).to_list(length=1)

            return {
                "collection": collection,
                "record_count": (
                    count_result[0]["record_count"]
                    if count_result
                    else 0
                ),
                "fields": {},
            }

        facets: dict[str, list[dict[str, Any]]] = {}

        for field in target_fields:
            facets[field] = [
                {
                    "$group": {
                        "_id": None,
                        "record_count": {
                            "$sum": 1,
                        },
                        "null_count": {
                            "$sum": {
                                "$cond": [
                                    {
                                        "$eq": [
                                            {
                                                "$ifNull": [
                                                    f"$data.{field}",
                                                    None,
                                                ]
                                            },
                                            None,
                                        ]
                                    },
                                    1,
                                    0,
                                ]
                            }
                        },
                        "missing_count": {
                            "$sum": {
                                "$cond": [
                                    {
                                        "$eq": [
                                            {
                                                "$type": f"$data.{field}",
                                            },
                                            "missing",
                                        ]
                                    },
                                    1,
                                    0,
                                ]
                            }
                        },
                        "distinct_values": {
                            "$addToSet": f"$data.{field}",
                        },
                        "min": {
                            "$min": f"$data.{field}",
                        },
                        "max": {
                            "$max": f"$data.{field}",
                        },
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "record_count": 1,
                        "null_count": 1,
                        "missing_count": 1,
                        "distinct_count": {
                            "$size": "$distinct_values",
                        },
                        "min": 1,
                        "max": 1,
                    }
                },
            ]

        result = await collection.aggregate(
            [
                match_stage,
                {
                    "$facet": facets,
                },
            ]
        ).to_list(length=1)

        if not result:
            return {
                "collection": collection,
                "record_count": 0,
                "fields": {},
            }

        facet_result = result[0]

        count_result = await collection.aggregate(
            [
                match_stage,
                {
                    "$count": "record_count",
                },
            ]
        ).to_list(length=1)

        record_count = (
            count_result[0]["record_count"]
            if count_result
            else 0
        )

        profile_fields: dict[str, Any] = {}

        for field in target_fields:
            rows = facet_result.get(field, [])

            if not rows:
                profile_fields[field] = {
                    "type": "unknown",
                    "null_count": 0,
                    "missing_count": record_count,
                    "distinct_count": 0,
                }
                continue

            row = rows[0]

            type_result = await collection.aggregate(
                [
                    match_stage,
                    {
                        "$group": {
                            "_id": {
                                "$type": f"$data.{field}",
                            },
                            "count": {
                                "$sum": 1,
                            },
                        }
                    },
                    {
                        "$sort": {
                            "count": -1,
                        }
                    },
                ]
            ).to_list(length=None)

            types = [
                item["_id"]
                for item in type_result
                if item["_id"] != "missing"
            ]

            profile_fields[field] = {
                "type": (
                    types[0]
                    if len(types) == 1
                    else "mixed"
                ),
                "types": types,
                "null_count": row.get(
                    "null_count",
                    0,
                ),
                "missing_count": row.get(
                    "missing_count",
                    0,
                ),
                "distinct_count": row.get(
                    "distinct_count",
                    0,
                ),
                "min": row.get("min"),
                "max": row.get("max"),
            }

        return {
            "collection": collection,
            "record_count": record_count,
            "fields": profile_fields,
        }

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

        collection = self._db[self.TABLE]

        if search_type not in SUPPORTED_SEARCH_TYPES:
            return []

        if search_type == "regex":
            try:
                re.compile(query)
            except re.error:
                return []

        if fields:
            search_fields = fields
        else:
            search_fields = None

        if search_fields:
            conditions = []

            for field in search_fields:
                field_path = f"data.{field}"

                if search_type == "exact":
                    conditions.append(
                        {
                            field_path: query,
                        }
                    )

                elif search_type == "phrase":
                    conditions.append(
                        {
                            field_path: {
                                "$regex": re.escape(query),
                                "$options": "i",
                            }
                        }
                    )

                elif search_type == "contains":
                    conditions.append(
                        {
                            field_path: {
                                "$regex": re.escape(query),
                                "$options": "i",
                            }
                        }
                    )

                elif search_type == "regex":
                    conditions.append(
                        {
                            field_path: {
                                "$regex": query,
                                "$options": "i",
                            }
                        }
                    )

            search_filter: dict[str, Any] = {
                "business_id": business_id,
                "object_type": collection,
                "$or": conditions,
            }

        else:
            escaped_query = (
                re.escape(query)
                if search_type != "regex"
                else query
            )

            regex_expression = (
                f"^{escaped_query}$"
                if search_type == "exact"
                else escaped_query
            )

            search_filter = {
                "business_id": business_id,
                "object_type": collection,
                "$expr": {
                    "$regexMatch": {
                        "input": {
                            "$toString": "$data"
                        },
                        "regex": regex_expression,
                        "options": "i",
                    }
                },
            }

        cursor = (
            collection.find(search_filter)
            .skip(offset)
            .limit(limit)
        )

        rows = await cursor.to_list(length=limit)

        return [
            self._normalize_document(row)
            for row in rows
        ]

    async def discover_relationships(
        self,
        *,
        business_id: str,
        collections: list[str] | None = None,
    ) -> list[dict[str, Any]]:

        collection = self._db[self.TABLE]

        match: dict[str, Any] = {
            "business_id": business_id,
        }

        if collections:
            match["object_type"] = {
                "$in": collections,
            }

        pipeline = [
            {
                "$match": match,
            },
            {
                "$project": {
                    "object_type": 1,
                    "fields": {
                        "$objectToArray": {
                            "$ifNull": [
                                "$data",
                                {},
                            ]
                        }
                    },
                }
            },
            {
                "$unwind": "$fields",
            },
            {
                "$group": {
                    "_id": {
                        "collection": "$object_type",
                        "field": "$fields.k",
                    },
                    "types": {
                        "$addToSet": {
                            "$type": "$fields.v",
                        }
                    },
                }
            },
            {
                "$group": {
                    "_id": "$_id.collection",
                    "fields": {
                        "$push": {
                            "name": "$_id.field",
                            "types": "$types",
                        }
                    },
                }
            },
        ]

        rows = await collection.aggregate(
            pipeline
        ).to_list(length=None)

        schemas: dict[str, dict[str, set[str]]] = {}

        for row in rows:
            collection_name = row["_id"]
            schemas[collection_name] = {}

            for field in row.get("fields", []):
                schemas[collection_name][
                    field["name"]
                ] = set(field.get("types", []))

        relationships: list[dict[str, Any]] = []

        collection_names = list(schemas)

        for fromcollection in collection_names:
            for tocollection in collection_names:
                if fromcollection == tocollection:
                    continue

                shared_fields = (
                    set(schemas[fromcollection])
                    & set(schemas[tocollection])
                )

                for field in shared_fields:
                    from_types = schemas[
                        fromcollection
                    ][field]

                    to_types = schemas[
                        tocollection
                    ][field]

                    relationships.append(
                        {
                            "fromcollection": fromcollection,
                            "from_field": field,
                            "tocollection": tocollection,
                            "to_field": field,
                            "confidence": (
                                "likely"
                                if from_types
                                & to_types
                                else "possible"
                            ),
                        }
                    )

        return relationships

    async def find_collections_path(
        self,
        *,
        business_id: str,
        fromcollection: str,
        tocollection: str,
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        relationships = await self.discover_relationships(
            business_id=business_id,
        )

        graph: dict[
            str,
            list[dict[str, Any]],
        ] = {}

        for relationship in relationships:
            graph.setdefault(
                relationship["fromcollection"],
                [],
            ).append(relationship)

        queue: list[
            tuple[
                str,
                list[dict[str, Any]],
            ]
        ] = [
            (
                fromcollection,
                [],
            )
        ]

        visited = {
            fromcollection,
        }

        while queue:
            current, path = queue.pop(0)

            if current == tocollection:
                return path

            if len(path) >= max_depth:
                continue

            for relationship in graph.get(
                current,
                [],
            ):
                nextcollection = relationship[
                    "tocollection"
                ]

                if nextcollection in visited:
                    continue

                visited.add(nextcollection)

                queue.append(
                    (
                        nextcollection,
                        path + [relationship],
                    )
                )

        return []

    async def aggregate_collection(
        self,
        *,
        business_id: str,
        collection: str,
        filters: dict[str, Any],
        group_by: list[str],
        metrics: list[dict[str, str]],
    ) -> list[dict[str, Any]]:

        collection = self._db[self.TABLE]

        match_filter: dict[str, Any] = {
            "business_id": business_id,
            "object_type": collection,
        }

        match_filter.update(
            self._build_data_filters(filters)
        )

        pipeline: list[dict[str, Any]] = [
            {
                "$match": match_filter,
            }
        ]

        group_id: dict[str, Any] = {}

        for field in group_by:
            group_id[field] = f"$data.{field}"

        accumulators: dict[str, Any] = {}

        for index, metric in enumerate(metrics):
            field = metric.get("field", "")
            operation = metric.get(
                "operation",
                "",
            )

            metric_name = self._metric_name(
                field,
                operation,
                index,
            )

            accumulators[
                metric_name
            ] = self._build_metric_accumulator(
                field=field,
                operation=operation,
            )

        if not group_by:
            pipeline.append(
                {
                    "$group": {
                        "_id": None,
                        **accumulators,
                    }
                }
            )
        else:
            pipeline.append(
                {
                    "$group": {
                        "_id": group_id,
                        **accumulators,
                    }
                }
            )

        project: dict[str, Any] = {
            "_id": 0,
        }

        for field in group_by:
            project[field] = f"$_id.{field}"

        for index, metric in enumerate(metrics):
            field = metric.get("field", "")
            operation = metric.get(
                "operation",
                "",
            )

            metric_name = self._metric_name(
                field,
                operation,
                index,
            )

            if operation == "distinct":
                project[metric_name] = {
                    "$size": {
                        "$ifNull": [
                            f"${metric_name}",
                            [],
                        ]
                    }
                }
            else:
                project[metric_name] = 1

        pipeline.append(
            {
                "$project": project,
            }
        )

        return await collection.aggregate(
            pipeline
        ).to_list(length=None)

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
        if len(collections) != 2:
            return []

        collection = self._db[self.TABLE]

        fromcollection = relationship[
            "fromcollection"
        ]
        from_field = relationship[
            "from_field"
        ]
        tocollection = relationship[
            "tocollection"
        ]
        to_field = relationship[
            "to_field"
        ]

        match_filter: dict[str, Any] = {
            "business_id": business_id,
            "object_type": fromcollection,
        }

        match_filter.update(
            self._build_data_filters(filters)
        )

        pipeline: list[dict[str, Any]] = [
            {
                "$match": match_filter,
            },
            {
                "$lookup": {
                    "from": self.TABLE,
                    "let": {
                        "relationship_value": (
                            f"$data.{from_field}"
                        )
                    },
                    "pipeline": [
                        {
                            "$match": {
                                "business_id": business_id,
                                "object_type": tocollection,
                            }
                        },
                        {
                            "$match": {
                                "$expr": {
                                    "$eq": [
                                        f"$data.{to_field}",
                                        "$$relationship_value",
                                    ]
                                }
                            }
                        },
                    ],
                    "as": "_related",
                }
            },
            {
                "$unwind": "$_related",
            },
        ]

        group_id: dict[str, Any] = {}

        for field in group_by:
            group_id[field] = self._related_field_path(
                field
            )

        accumulators: dict[str, Any] = {}

        for index, metric in enumerate(metrics):
            field = metric.get("field", "")
            operation = metric.get(
                "operation",
                "",
            )

            metric_name = self._metric_name(
                field,
                operation,
                index,
            )

            accumulators[
                metric_name
            ] = self._build_related_metric_accumulator(
                field=field,
                operation=operation,
            )

        pipeline.append(
            {
                "$group": {
                    "_id": (
                        group_id
                        if group_by
                        else None
                    ),
                    **accumulators,
                }
            }
        )

        project: dict[str, Any] = {
            "_id": 0,
        }

        for field in group_by:
            project[field] = f"$_id.{field}"

        for index, metric in enumerate(metrics):
            field = metric.get("field", "")
            operation = metric.get(
                "operation",
                "",
            )

            metric_name = self._metric_name(
                field,
                operation,
                index,
            )

            if operation == "distinct":
                project[metric_name] = {
                    "$size": {
                        "$ifNull": [
                            f"${metric_name}",
                            [],
                        ]
                    }
                }
            else:
                project[metric_name] = 1

        pipeline.append(
            {
                "$project": project,
            }
        )

        return await collection.aggregate(
            pipeline
        ).to_list(length=None)

    async def traverse_relationships(
        self,
        *,
        business_id: str,
        startcollection: str,
        relationships: list[dict[str, str]],
        filters: dict[str, Any],
        fields: list[str],
        limit: int = 20,
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        if not relationships:
            return []

        if len(relationships) > max_depth:
            return []

        collection = self._db[self.TABLE]

        match_filter: dict[str, Any] = {
            "business_id": business_id,
            "object_type": startcollection,
        }

        match_filter.update(
            self._build_data_filters(filters)
        )

        pipeline: list[dict[str, Any]] = [
            {
                "$match": match_filter,
            }
        ]

        currentcollection = startcollection

        for index, relationship in enumerate(
            relationships
        ):
            if (
                relationship["fromcollection"]
                != currentcollection
            ):
                return []

            from_field = relationship[
                "from_field"
            ]

            tocollection = relationship[
                "tocollection"
            ]

            to_field = relationship[
                "to_field"
            ]

            related_name = (
                f"_relationship_{index}"
            )

            pipeline.append(
                {
                    "$lookup": {
                        "from": self.TABLE,
                        "let": {
                            "relationship_value": (
                                f"$data.{from_field}"
                            )
                        },
                        "pipeline": [
                            {
                                "$match": {
                                    "business_id": business_id,
                                    "object_type": tocollection,
                                }
                            },
                            {
                                "$match": {
                                    "$expr": {
                                        "$eq": [
                                            f"$data.{to_field}",
                                            "$$relationship_value",
                                        ]
                                    }
                                }
                            },
                        ],
                        "as": related_name,
                    }
                }
            )

            pipeline.append(
                {
                    "$unwind": f"${related_name}",
                }
            )

            pipeline.append(
                {
                    "$replaceRoot": {
                        "newRoot": f"${related_name}",
                    }
                }
            )

            currentcollection = tocollection

        pipeline.append(
            {
                "$limit": limit,
            }
        )

        if fields:
            projection = {
                "_id": 0,
            }

            for field in fields:
                projection[field] = f"$data.{field}"

            pipeline.append(
                {
                    "$project": projection,
                }
            )
        else:
            pipeline.append(
                {
                    "$project": {
                        "_id": 0,
                        "data": 1,
                        "object_type": 1,
                        "business_id": 1,
                        "status": 1,
                    }
                }
            )

        return await collection.aggregate(
            pipeline
        ).to_list(length=limit)

    @staticmethod
    def _build_data_filters(
        filters: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            f"data.{field}": value
            for field, value in filters.items()
        }

    @staticmethod
    def _metric_name(
        field: str,
        operation: str,
        index: int,
    ) -> str:
        if operation == "count":
            if field:
                return f"count_{field}"

            return "count"

        if field:
            return f"{operation}_{field}"

        return f"{operation}_{index}"

    @staticmethod
    def _build_metric_accumulator(
        *,
        field: str,
        operation: str,
    ) -> dict[str, Any]:
        field_path = (
            f"$data.{field}"
            if field
            else None
        )

        if operation == "count":
            if field:
                return {
                    "$sum": {
                        "$cond": [
                            {
                                "$ne": [
                                    field_path,
                                    None,
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                }

            return {
                "$sum": 1,
            }

        if operation == "sum":
            return {
                "$sum": field_path,
            }

        if operation == "average":
            return {
                "$avg": field_path,
            }

        if operation == "min":
            return {
                "$min": field_path,
            }

        if operation == "max":
            return {
                "$max": field_path,
            }

        if operation == "median":
            return {
                "$median": {
                    "input": field_path,
                    "method": "approximate",
                }
            }

        if operation == "distinct":
            return {
                "$addToSet": field_path,
            }

        if operation == "standard_deviation":
            return {
                "$stdDevPop": field_path,
            }

        if operation == "percentile":
            return {
                "$percentile": {
                    "input": field_path,
                    "p": [0.95],
                    "method": "approximate",
                }
            }

        return {
            "$sum": 0,
        }

    @staticmethod
    def _build_related_metric_accumulator(
        *,
        field: str,
        operation: str,
    ) -> dict[str, Any]:
        field_path = (
            EntityRepository._related_field_path(
                field
            )
        )

        if operation == "count":
            if field:
                return {
                    "$sum": {
                        "$cond": [
                            {
                                "$ne": [
                                    field_path,
                                    None,
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                }

            return {
                "$sum": 1,
            }

        if operation == "sum":
            return {
                "$sum": field_path,
            }

        if operation == "average":
            return {
                "$avg": field_path,
            }

        if operation == "min":
            return {
                "$min": field_path,
            }

        if operation == "max":
            return {
                "$max": field_path,
            }

        if operation == "median":
            return {
                "$median": {
                    "input": field_path,
                    "method": "approximate",
                }
            }

        if operation == "distinct":
            return {
                "$addToSet": field_path,
            }

        if operation == "standard_deviation":
            return {
                "$stdDevPop": field_path,
            }

        if operation == "percentile":
            return {
                "$percentile": {
                    "input": field_path,
                    "p": [0.95],
                    "method": "approximate",
                }
            }

        return {
            "$sum": 0,
        }

    @staticmethod
    def _related_field_path(
        field: str,
    ) -> str:
        if field.startswith("from."):
            return f"$data.{field[5:]}"

        if field.startswith("to."):
            return f"$_related.data.{field[3:]}"

        return f"$data.{field}"

    @staticmethod
    def _normalize_document(
        document: dict[str, Any],
    ) -> dict[str, Any]:
        if "_id" in document:
            document["id"] = str(
                document.pop("_id")
            )

        return document
