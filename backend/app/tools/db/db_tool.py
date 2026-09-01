from __future__ import annotations
from typing import Any, Literal


from typing import Any

from langchain_core.tools import tool

from ...business_cores.entities.config.service import (
    EntityConfigService,
    entity_config_service,
)
from ...business_cores.entities.service import EntityService, entity_service


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

UNSUPPORTED_REGEX_TOKENS = (
    "(?=",
    "(?!",
    "(?<=",
    "(?<!",
    "(?>",
    "(?P<",
    "(?P=",
    "(?(",
    "(?i",
    "(?m",
    "(?s",
    "(?x",
    "(?-",
    "\\1",
    "\\2",
    "\\3",
    "\\4",
    "\\5",
    "\\6",
    "\\7",
    "\\8",
    "\\9",
    "\\g<",
)


def create_list_business_entities_tool(
    *,
    config_service: EntityConfigService = entity_config_service,
    business_id: str,
):
    @tool(
        "list_business_entities",
        description=(
            """
            List the business entities available in the business.

            Use this tool when you need to discover which business
            entities are available and which fields can be used to
            search them.

            The result contains each entity type and its available
            fields.

            Use limit and offset to paginate through large entity catalogs.
            """
        ),
    )
    async def list_business_entities(
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        try:
            if not isinstance(limit, int):
                return {
                    "error": "limit must be an integer"
                }

            if not isinstance(offset, int):
                return {
                    "error": "offset must be an integer"
                }

            if limit < 1 or limit > 100:
                return {
                    "error": "limit must be between 1 and 100"
                }

            if offset < 0:
                return {
                    "error": "offset cannot be negative"
                }

            return await config_service.list_object_types(
                business_id=business_id,
                limit=limit,
                offset=offset,
            )

        except Exception as exc:
            return {
                "error": "Failed to list business entities",

            }

    return list_business_entities


def create_search_business_entities_tool(
    *,
    entity_service: EntityService = entity_service,
    business_id: str,
):
    @tool(
        "search_business_entities",
        description=(
            """
            Search business entities using their available business fields.

            Provide the entity type and field values that the entity
            should match.

            Example:
            entity_type="customer"
            filters={"name": customer_name, ...}

            Multiple fields can be provided. When multiple fields are
            provided, the entity must match all supplied fields.

            Use list_business_entities first if you do not know the
            available entity types or fields.

            Filters must contain only business field names and their
            corresponding values.

            Do not construct database queries or use database-specific
            operators. The runtime handles database query construction.

            Use limit to paginate through entities returned.
            """
        ),
    )
    async def search_business_entities(
        entity_type: str,
        filters: dict[str, Any],
        limit: int = 20,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        try:
            if not isinstance(entity_type, str):
                return {
                    "error": "entity_type must be a string"
                }

            entity_type = entity_type.strip()

            if not entity_type:
                return {
                    "error": "entity_type cannot be empty"
                }

            if not isinstance(filters, dict):
                return {
                    "error": "filters must be an object"
                }

            if not isinstance(limit, int):
                return {
                    "error": "limit must be an integer"
                }

            if limit < 1 or limit > 100:
                return {
                    "error": "limit must be between 1 and 100"
                }

            return await entity_service.search(
                business_id=business_id,
                object_type=entity_type,
                filters=filters,
                limit=limit,
            )

        except Exception as exc:
            return {
                "error": "Failed to search business entities",

            }

    return search_business_entities


def create_inspect_database_tool(
    *,
    entity_service: EntityService = entity_service,
    business_id: str,
):
    @tool(
        "inspect_business_data",
        description=(
            """
            Inspect the available business data in the database.

            Returns the available business-related collections and the
            fields found in each collection.

            Use this tool when you need to understand what business data
            is available before inspecting or querying a specific
            collection.

            Use limit and offset to paginate through collections.
            """
        ),
    )
    async def inspect_database(
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        try:
            if not isinstance(limit, int):
                return {
                    "error": "limit must be an integer"
                }

            if not isinstance(offset, int):
                return {
                    "error": "offset must be an integer"
                }

            if limit < 1 or limit > 100:
                return {
                    "error": "limit must be between 1 and 100"
                }

            if offset < 0:
                return {
                    "error": "offset cannot be negative"
                }

            return await entity_service.inspect_database(
                business_id=business_id,
                limit=limit,
                offset=offset,
            )

        except Exception as exc:
            return {
                "error": "Failed to inspect database",

            }

    return inspect_database


def create_inspect_collection_tool(
    *,
    entity_service: EntityService = entity_service,
    business_id: str,
):
    @tool(
        "inspect_collection",
        description=(
            """
            Inspect one or more business data collections.

            Use inspect_business_data first to discover available collections.

            Provide one or more collection names returned by
            inspect_business_data.

            For a single collection, the tool returns its detailed
            structure directly.

            For multiple collections, the tool supports pagination
            using limit and offset.

            Returns detailed information about the selected collections,
            including their available fields and data structure.
            """
        ),
    )
    async def inspect_collection(
        collections: list[str],
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        try:
            if not isinstance(collections, list):
                return {
                    "error": "collections must be an array of collection names"
                }

            if not collections:
                return {
                    "error": "At least one collection name must be provided"
                }

            if any(
                not isinstance(collection, str) or not collection.strip()
                for collection in collections
            ):
                return {
                    "error": "Each collection name must be a non-empty string"
                }

            collections = [
                collection.strip()
                for collection in collections
            ]

            if len(collections) == 1:
                return await entity_service.inspect_collection(
                    business_id=business_id,
                    collection=collections[0],
                )

            if not isinstance(limit, int):
                return {
                    "error": "limit must be an integer"
                }

            if not isinstance(offset, int):
                return {
                    "error": "offset must be an integer"
                }

            if limit < 1 or limit > 100:
                return {
                    "error": "limit must be between 1 and 100"
                }

            if offset < 0:
                return {
                    "error": "offset cannot be negative"
                }

            return await entity_service.inspect_collections(
                business_id=business_id,
                collections=collections,
                limit=limit,
                offset=offset,
            )

        except Exception as exc:
            return {
                "error": "Failed to inspect collection",

            }

    return inspect_collection


def create_query_database_tool(
    *,
    entity_service: EntityService = entity_service,
    business_id: str,
):
    @tool(
        "query_business_records",
        description=(
            """
            Query business record from an available business collection.

            Use inspect_business_data to discover available collections.
            Use inspect_collection when you need to understand the
            structure or fields of a collection before querying it.

            Provide the collection name and business field filters.

            Filters must contain field names and their corresponding
            values. Do not construct MongoDB queries or use database-
            specific operators.

            Multiple filters are matched together.

            Use limit and offset to paginate through results.
            """
        ),
    )
    async def query_database(
        collection: str,
        filters: dict[str, Any],
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        try:
            if not isinstance(collection, str):
                return {
                    "error": "collection must be a string"
                }

            collection = collection.strip()

            if not collection:
                return {
                    "error": "collection must be a non-empty string"
                }

            if not isinstance(filters, dict):
                return {
                    "error": "filters must be an object"
                }

            if not isinstance(limit, int):
                return {
                    "error": "limit must be an integer"
                }

            if not isinstance(offset, int):
                return {
                    "error": "offset must be an integer"
                }

            if limit < 1 or limit > 100:
                return {
                    "error": "limit must be between 1 and 100"
                }

            if offset < 0:
                return {
                    "error": "offset cannot be negative"
                }

            return await entity_service.query_collection(
                business_id=business_id,
                collection=collection,
                filters=filters,
                limit=limit,
                offset=offset,
            )

        except Exception as exc:
            return {
                "error": "Failed to query database",
            }

    return query_database


def create_profile_collection_tool(
    *,
    entity_service: EntityService = entity_service,
    business_id: str,
):
    @tool(
        "profile_collection",
        description=(
            """
            Profile the actual data distribution of a business collection.

            Use inspect_collection first when you need to understand the
            available fields.

            This tool helps understand the contents and distribution of
            data without retrieving all records.

            It can return field types, null or missing counts,
            distinct value counts, common values, and numeric or
            date ranges.

            Provide specific fields when you only need to profile selected
            fields. If fields are omitted, profile the relevant fields
            available in the collection.

            Use business field names only.
            """
        ),
    )
    async def profile_collection(
        collection: str,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        try:
            if not isinstance(collection, str):
                return {
                    "error": "collection must be a string"
                }

            collection = collection.strip()

            if not collection:
                return {
                    "error": "collection must be a non-empty string"
                }

            if fields is not None:
                if not isinstance(fields, list):
                    return {
                        "error": "fields must be an array of field names"
                    }

                if any(
                    not isinstance(field, str) or not field.strip()
                    for field in fields
                ):
                    return {
                        "error": "Each field must be a non-empty string"
                    }

                fields = [
                    field.strip()
                    for field in fields
                ]

            return await entity_service.profile_collection(
                business_id=business_id,
                collection=collection,
                fields=fields,
            )

        except Exception as exc:
            return {
                "error": "Failed to profile collection",

            }

    return profile_collection


def create_discover_relationships_tool(
    *,
    entity_service: EntityService = entity_service,
    business_id: str,
):
    @tool(
        "discover_relationships",
        description=(
            """
            Discover relationships between business data collections.

            Use inspect_business_data first when you need to discover the
            available collections.

            This tool identifies likely relationships between collections
            and the fields that connect them.

            Provide collection names to limit discovery to specific
            collections.

            If collections are omitted, discover relationships across
            the available business data.

            Use business collection and field names only.
            """
        ),
    )
    async def discover_relationships(
        collections: list[str] | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        try:
            if collections is not None:
                if not isinstance(collections, list):
                    return {
                        "error": (
                            "collections must be an array of collection names"
                        )
                    }

                if not collections:
                    return {
                        "error": "collections cannot be empty when provided"
                    }

                if any(
                    not isinstance(collection, str)
                    or not collection.strip()
                    for collection in collections
                ):
                    return {
                        "error": (
                            "Each collection name must be a non-empty string"
                        )
                    }

                collections = [
                    collection.strip()
                    for collection in collections
                ]

            return await entity_service.discover_relationships(
                business_id=business_id,
                collections=collections,
            )

        except Exception as exc:
            return {
                "error": "Failed to discover relationships",

            }

    return discover_relationships


def create_aggregate_database_tool(
    *,
    entity_service: EntityService = entity_service,
    business_id: str,
):
    supported_operations = ", ".join(
        SUPPORTED_AGGREGATION_OPERATIONS
    )

    @tool(
        "aggregate_database",
        description=(
            f"""
            Analyze business data from a collection using aggregations.

            Use inspect_business_data to discover available collections.

            Use inspect_collection to understand the available fields.

            Use filters to restrict which business records are included.

            Use group_by to organize results by one or more business fields.

            Use metrics to calculate values for specific fields.

            Each metric must contain:

            - field: the business field to analyze
            - operation: the aggregation operation to perform

            Supported aggregation operations:

            {supported_operations}

            Operation meanings:
            
            - count: count records
            - sum: calculate the total of a numeric field
            - average: calculate the average of a numeric field
            - min: find the minimum value
            - max: find the maximum value
            - median: find the middle value
            - distinct: count distinct values
            - standard_deviation: measure value distribution
            - percentile: calculate a percentile value

            IMPORTANT:
            Only use the supported aggregation operations listed above.
            Do not invent operation names or use operations outside this list.

            Example:

            collection="<collection 1>"
            filters={{"<field>": "<value>"}}
            group_by=["<value>"]
            metrics=[
                {{"field": "<field value>", "operation": "sum"}},
                {{"field": "<field value>", "operation": "average"}},
                {{"field": "<field value>", "operation": "count"}}
            ]

            Use business collection and field names only.
            """
        ),
    )
    async def aggregate_database(
        collection: str,
        filters: dict[str, Any] | None = None,
        group_by: list[str] | None = None,
        metrics: list[dict[str, str]] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        try:
            if not isinstance(collection, str):
                return {
                    "error": "collection must be a string"
                }

            collection = collection.strip()

            if not collection:
                return {
                    "error": "collection must be a non-empty string"
                }

            if filters is not None and not isinstance(filters, dict):
                return {
                    "error": "filters must be an object"
                }

            if group_by is not None:
                if not isinstance(group_by, list):
                    return {
                        "error": "group_by must be an array of field names"
                    }

                if any(
                    not isinstance(field, str) or not field.strip()
                    for field in group_by
                ):
                    return {
                        "error": (
                            "Each group_by field must be "
                            "a non-empty string"
                        )
                    }

                group_by = [
                    field.strip()
                    for field in group_by
                ]

            if metrics is not None:
                if not isinstance(metrics, list):
                    return {
                        "error": "metrics must be an array"
                    }

                normalized_metrics: list[dict[str, str]] = []

                for metric in metrics:
                    if not isinstance(metric, dict):
                        return {
                            "error": "Each metric must be an object"
                        }

                    field = metric.get("field")
                    operation = metric.get("operation")

                    if not isinstance(field, str):
                        return {
                            "error": (
                                "Each metric must contain "
                                "a string field"
                            )
                        }

                    field = field.strip()

                    if not field:
                        return {
                            "error": "Metric field cannot be empty"
                        }

                    if not isinstance(operation, str):
                        return {
                            "error": (
                                "Each metric must contain "
                                "an operation"
                            )
                        }

                    operation = operation.strip().lower()

                    if operation not in SUPPORTED_AGGREGATION_OPERATIONS:
                        return {
                            "error": (
                                f"Unsupported aggregation operation: "
                                f"'{operation}'. "
                                f"Supported operations are: "
                                f"{', '.join(SUPPORTED_AGGREGATION_OPERATIONS)}"
                            )
                        }

                    normalized_metrics.append(
                        {
                            "field": field,
                            "operation": operation,
                        }
                    )

                metrics = normalized_metrics

            return await entity_service.aggregate_collection(
                business_id=business_id,
                collection=collection,
                filters=filters or {},
                group_by=group_by or [],
                metrics=metrics or [],
            )

        except Exception as exc:
            return {
                "error": "Failed to aggregate business data",

            }

    return aggregate_database


def create_aggregate_related_data_tool(
    *,
    entity_service: EntityService = entity_service,
    business_id: str,
):

    supported_operations = ", ".join(
        SUPPORTED_AGGREGATION_OPERATIONS
    )

    @tool(
        "aggregate_related_data",
        description=(
            f"""
            Analyze business data across directly related collections.

            Use inspect_business_data first to discover available collections.

            Use inspect_collection to understand the fields available
            in the collections.

            Use discover_relationships to identify valid relationships
            between the collections before using this tool.

            This tool is for aggregation across two directly related
            collections.

            Use filters to restrict which business records are included.

            Use group_by to organize the results by business fields.

            Use metrics to calculate values across the related data.

            Each metric must contain:

            - field: the business field to analyze
            - operation: the aggregation operation to perform

            Supported aggregation operations:
            {supported_operations}

            Operation meanings:
            - count: count records
            - sum: calculate the total of a numeric field
            - average: calculate the average of a numeric field
            - min: find the minimum value
            - max: find the maximum value
            - median: find the middle value
            - distinct: count distinct values
            - standard_deviation: measure value distribution
            - percentile: calculate a percentile value

            IMPORTANT:
            Only use supported aggregation operations.
            Do not invent operation names.

            Example:

            collections=["collection 1", "collection 2"]

            relationship={{
                "from_collection": "<collection 1>",
                "from_field": "<field value>",
                "to_collection": "<collection 2>",
                "to_field": "<field value>"
            }}

            group_by=["customers.country"]

            metrics=[
                {{
                    "field": "<collection 1>.<field value>",
                    "operation": "sum"
                }},
                {{
                    "field": "<collection 2>.<field value>",
                    "operation": "count"
                }}
            ]

            Use business collection and field names only.
            """
        ),
    )
    async def aggregate_related_data(
        collections: list[str],
        relationship: dict[str, str],
        filters: dict[str, Any] | None = None,
        group_by: list[str] | None = None,
        metrics: list[dict[str, str]] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        try:
            if not isinstance(collections, list):
                return {
                    "error": "collections must be an array of collection names"
                }

            if len(collections) != 2:
                return {
                    "error": (
                        "aggregate_related_data requires exactly "
                        "two directly related collections"
                    )
                }

            if any(
                not isinstance(collection, str) or not collection.strip()
                for collection in collections
            ):
                return {
                    "error": (
                        "Each collection name must be a "
                        "non-empty string"
                    )
                }

            collections = [
                collection.strip()
                for collection in collections
            ]

            if not isinstance(relationship, dict):
                return {
                    "error": "relationship must be an object"
                }

            required_relationship_fields = (
                "from_collection",
                "from_field",
                "to_collection",
                "to_field",
            )

            for field in required_relationship_fields:
                value = relationship.get(field)

                if not isinstance(value, str) or not value.strip():
                    return {
                        "error": (
                            f"relationship.{field} must be a "
                            "non-empty string"
                        )
                    }

            relationship = {
                key: value.strip()
                for key, value in relationship.items()
            }

            if (
                relationship["from_collection"] not in collections
                or relationship["to_collection"] not in collections
            ):
                return {
                    "error": (
                        "The relationship collections must match "
                        "the two provided collections"
                    )
                }

            if filters is not None and not isinstance(filters, dict):
                return {
                    "error": "filters must be an object"
                }

            if group_by is not None:
                if not isinstance(group_by, list):
                    return {
                        "error": (
                            "group_by must be an array "
                            "of field names"
                        )
                    }

                if any(
                    not isinstance(field, str) or not field.strip()
                    for field in group_by
                ):
                    return {
                        "error": (
                            "Each group_by field must be "
                            "a non-empty string"
                        )
                    }

                group_by = [
                    field.strip()
                    for field in group_by
                ]

            if metrics is not None:
                if not isinstance(metrics, list):
                    return {
                        "error": "metrics must be an array"
                    }

                normalized_metrics: list[dict[str, str]] = []

                for metric in metrics:
                    if not isinstance(metric, dict):
                        return {
                            "error": "Each metric must be an object"
                        }

                    field = metric.get("field")
                    operation = metric.get("operation")

                    if not isinstance(field, str):
                        return {
                            "error": (
                                "Each metric must contain "
                                "a string field"
                            )
                        }

                    field = field.strip()

                    if not field:
                        return {
                            "error": "Metric field cannot be empty"
                        }

                    if not isinstance(operation, str):
                        return {
                            "error": (
                                "Each metric must contain "
                                "an operation"
                            )
                        }

                    operation = operation.strip().lower()

                    if operation not in SUPPORTED_AGGREGATION_OPERATIONS:
                        return {
                            "error": (
                                f"Unsupported aggregation operation: "
                                f"'{operation}'. "
                                f"Supported operations are: "
                                f"{', '.join(SUPPORTED_AGGREGATION_OPERATIONS)}"
                            )
                        }

                    normalized_metrics.append(
                        {
                            "field": field,
                            "operation": operation,
                        }
                    )

                metrics = normalized_metrics

            return await entity_service.aggregate_related_data(
                business_id=business_id,
                collections=collections,
                relationship=relationship,
                filters=filters or {},
                group_by=group_by or [],
                metrics=metrics or [],
            )

        except Exception as exc:
            return {
                "error": "Failed to aggregate related business data",

            }

    return aggregate_related_data


def create_traverse_relationships_tool(
    *,
    entity_service: EntityService = entity_service,
    business_id: str,
):
    @tool(
        "traverse_relationships",
        description=(
            """
            Traverse a chain of relationships across business data
            collections.

            Use inspect_business_data first to discover available collections.

            Use inspect_collection to understand the fields available
            in the collections.

            Use discover_relationships to identify valid relationships
            before using this tool.

            This tool is for following multiple related collections
            in sequence.

            A relationship chain connects one collection to the next.

            Example:

            customers
            -> <collection 1>
            -> <collection 2>
            -> <collection 3>

            Each relationship must contain:

            - from_collection: the collection where the relationship starts
            - from_field: the business field used from that collection
            - to_collection: the related collection
            - to_field: the business field used in the related collection

            The relationships must form a continuous chain.

            Example:

            start_collection="<collection 1>"

            relationships=[
                {
                    "from_collection": "<collection 1>",
                    "from_field": "<field value>",
                    "to_collection": "<collection 2>",
                    "to_field": "<field value>"
                },
                {
                    "from_collection": "<collection 2>",
                    "from_field": "<field value>",
                    "to_collection": "<collection 1>",
                    "to_field": "<field value>"
                },
                {
                    "from_collection": "<collection 3>",
                    "from_field": "<field value>",
                    "to_collection": "<collection 2>",
                    "to_field": "<field value>"
                }
            ]

            The maximum relationship depth is 5 by default and
            cannot exceed 10.

            Use filters to restrict the business data being traversed.

            Use fields to specify which business fields should be
            returned from the relationship chain.

            Use limit to control the maximum number of results.

            Do not invent collection names or field names.
            Use relationships discovered from the business data.
            """
        ),
    )
    async def traverse_relationships(
        start_collection: str,
        relationships: list[dict[str, str]],
        filters: dict[str, Any] | None = None,
        fields: list[str] | None = None,
        limit: int = 20,
        max_depth: int = 5,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        try:
            if not isinstance(start_collection, str):
                return {
                    "error": "start_collection must be a string"
                }

            start_collection = start_collection.strip()

            if not start_collection:
                return {
                    "error": (
                        "start_collection must be "
                        "a non-empty string"
                    )
                }

            if not isinstance(relationships, list):
                return {
                    "error": "relationships must be an array"
                }

            if not relationships:
                return {
                    "error": "relationships cannot be empty"
                }

            if not isinstance(max_depth, int):
                return {
                    "error": "max_depth must be an integer"
                }

            if max_depth < 1 or max_depth > 10:
                return {
                    "error": "max_depth must be between 1 and 10"
                }

            if len(relationships) > max_depth:
                return {
                    "error": (
                        f"Relationship chain exceeds the maximum "
                        f"depth of {max_depth}"
                    )
                }

            normalized_relationships: list[dict[str, str]] = []

            required_fields = (
                "from_collection",
                "from_field",
                "to_collection",
                "to_field",
            )

            expected_collection = start_collection

            for index, relationship in enumerate(relationships):
                if not isinstance(relationship, dict):
                    return {
                        "error": (
                            f"Relationship at index {index} "
                            "must be an object"
                        )
                    }

                for field in required_fields:
                    value = relationship.get(field)

                    if not isinstance(value, str) or not value.strip():
                        return {
                            "error": (
                                f"Relationship at index {index} "
                                f"must contain a non-empty "
                                f"{field}"
                            )
                        }

                normalized_relationship = {
                    key: value.strip()
                    for key, value in relationship.items()
                }

                if (
                    normalized_relationship["from_collection"]
                    != expected_collection
                ):
                    return {
                        "error": (
                            f"Relationship at index {index} "
                            "does not continue the relationship "
                            f"chain. Expected from_collection "
                            f"'{expected_collection}'"
                        )
                    }

                expected_collection = (
                    normalized_relationship["to_collection"]
                )

                normalized_relationships.append(
                    normalized_relationship
                )

            if filters is not None and not isinstance(filters, dict):
                return {
                    "error": "filters must be an object"
                }

            if fields is not None:
                if not isinstance(fields, list):
                    return {
                        "error": (
                            "fields must be an array "
                            "of field names"
                        )
                    }

                if any(
                    not isinstance(field, str) or not field.strip()
                    for field in fields
                ):
                    return {
                        "error": (
                            "Each field must be "
                            "a non-empty string"
                        )
                    }

                fields = [
                    field.strip()
                    for field in fields
                ]

            if not isinstance(limit, int):
                return {
                    "error": "limit must be an integer"
                }

            if limit < 1 or limit > 100:
                return {
                    "error": "limit must be between 1 and 100"
                }

            return await entity_service.traverse_relationships(
                business_id=business_id,
                start_collection=start_collection,
                relationships=normalized_relationships,
                filters=filters or {},
                fields=fields or [],
                limit=limit,
                max_depth=max_depth,
            )

        except Exception as exc:
            return {
                "error": "Failed to traverse business relationships",

            }

    return traverse_relationships


def create_search_business_data_tool(
    *,
    entity_service: EntityService = entity_service,
    business_id: str,
):
    @tool(
        "search_business_records",
        description=(
            f"""
            Search business record for text, keywords, phrases, or
            supported regular expression patterns.

            Use this tool when you need to find specific words,
            phrases, text patterns, or matching content in business
            records.

            Use inspect_business_data first when you need to discover
            available collections.

            Use inspect_collection first when you need to understand
            the fields available in a collection.

            Supported search types:
            {", ".join(SUPPORTED_SEARCH_TYPES)}

            Search type meanings:

            - exact: match the exact search value
            - phrase: search for an exact phrase
            - contains: search for records containing the search value
            - regex: match using the supported regular expression pattern

            For regex searches, only the following pattern syntax is
            supported:

            - literal characters
            - . : match any single character
            - * : match zero or more of the previous character or group
            - + : match one or more of the previous character or group
            - ? : match zero or one of the previous character or group
            - ^ : match the beginning of the text
            - $ : match the end of the text
            - [...] : character classes
            - (...) : grouped expressions
            - | : OR between expressions

            The following regex constructs are explicitly unsupported:
            {", ".join(UNSUPPORTED_REGEX_TOKENS)}

            Do not use regex escape sequences, lookahead, lookbehind,
            backreferences, inline flags, or other unsupported regex
            constructs.

            Use fields to restrict the search to specific business fields.

            Use limit to control the maximum number of matching records.

            Use offset to paginate through matching records.

            Search using business collection and field names only.

            Do not use database query syntax or operators.
            """
        ),
    )
    async def search_business_data(
        collection: str,
        query: str,
        search_type: Literal[
            "exact",
            "phrase",
            "contains",
            "regex",
        ] = "contains",
        fields: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        try:
            if not isinstance(collection, str):
                return {
                    "error": "collection must be a string"
                }

            collection = collection.strip()

            if not collection:
                return {
                    "error": (
                        "collection must be a non-empty string"
                    )
                }

            if not isinstance(query, str):
                return {
                    "error": "query must be a string"
                }

            query = query.strip()

            if not query:
                return {
                    "error": "query must be a non-empty string"
                }

            if not isinstance(search_type, str):
                return {
                    "error": "search_type must be a string"
                }

            search_type = search_type.strip().lower()

            if search_type not in SUPPORTED_SEARCH_TYPES:
                return {
                    "error": (
                        f"Unsupported search type: "
                        f"'{search_type}'. "
                        f"Supported search types are: "
                        f"{', '.join(SUPPORTED_SEARCH_TYPES)}"
                    )
                }

            if search_type == "regex":
                if len(query) > 200:
                    return {
                        "error": (
                            "Regex pattern must not exceed "
                            "200 characters"
                        )
                    }

                if "\\" in query:
                    return {
                        "error": (
                            "Regex escape sequences are not supported"
                        )
                    }

                for token in UNSUPPORTED_REGEX_TOKENS:
                    if token in query:
                        return {
                            "error": (
                                f"Unsupported regex construct: "
                                f"'{token}'"
                            )
                        }

                try:
                    import re

                    re.compile(query)

                except re.error as exc:
                    return {
                        "error": "Invalid regex pattern",
                        "details": str(exc),
                    }

            if fields is not None:
                if not isinstance(fields, list):
                    return {
                        "error": (
                            "fields must be an array "
                            "of field names"
                        )
                    }

                if any(
                    not isinstance(field, str) or not field.strip()
                    for field in fields
                ):
                    return {
                        "error": (
                            "Each field must be "
                            "a non-empty string"
                        )
                    }

                fields = [
                    field.strip()
                    for field in fields
                ]

            if not isinstance(limit, int):
                return {
                    "error": "limit must be an integer"
                }

            if limit < 1 or limit > 100:
                return {
                    "error": "limit must be between 1 and 100"
                }

            if not isinstance(offset, int):
                return {
                    "error": "offset must be an integer"
                }

            if offset < 0:
                return {
                    "error": (
                        "offset must be greater than or equal to 0"
                    )
                }

            return await entity_service.search_business_data(
                business_id=business_id,
                collection=collection,
                query=query,
                search_type=search_type,
                fields=fields or [],
                limit=limit,
                offset=offset,
            )

        except Exception as exc:
            return {
                "error": "Failed to search business data",
                "details": str(exc),
            }

    return search_business_data


def create_find_collections_path_tool(
    *,
    entity_service: EntityService = entity_service,
    business_id: str,
):
    @tool(
        "find_collections_path",
        description=(
            """
            Find a relationship path between two business data
            collections.

            Use inspect_business_data first to discover available collections.

            Use discover_relationships to identify relationships
            between the available collections.

            Use this tool when two collections are not directly related
            and you need to determine how they can be connected through
            one or more intermediate collections.

            The result contains the relationship chain connecting the
            starting collection to the target collection.

            Use max_depth to control the maximum number of relationships
            that may be included in the path.

            The maximum path depth is 5 by default and cannot exceed 10.

            This tool finds the path only. It does not retrieve business
            records or perform aggregation.

            Use the returned relationship path with
            traverse_relationships when you need to retrieve data
            across the relationship chain.

            Use business collection and field names only.
            Do not invent collection names or field names.
            """
        ),
    )
    async def find_collections_path(
        from_collection: str,
        to_collection: str,
        max_depth: int = 5,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        try:
            if not isinstance(from_collection, str):
                return {
                    "error": "from_collection must be a string"
                }

            from_collection = from_collection.strip()

            if not from_collection:
                return {
                    "error": (
                        "from_collection must be "
                        "a non-empty string"
                    )
                }

            if not isinstance(to_collection, str):
                return {
                    "error": "to_collection must be a string"
                }

            to_collection = to_collection.strip()

            if not to_collection:
                return {
                    "error": (
                        "to_collection must be "
                        "a non-empty string"
                    )
                }

            if not isinstance(max_depth, int):
                return {
                    "error": "max_depth must be an integer"
                }

            if max_depth < 1 or max_depth > 10:
                return {
                    "error": "max_depth must be between 1 and 10"
                }

            if from_collection == to_collection:
                return {
                    "error": (
                        "from_collection and to_collection "
                        "must be different"
                    )
                }

            return await entity_service.find_collections_path(
                business_id=business_id,
                from_collection=from_collection,
                to_collection=to_collection,
                max_depth=max_depth,
            )

        except Exception as exc:
            return {
                "error": "Failed to find collection relationship path",

            }

    return find_collections_path


def get_db_tool(business_id: str) -> list:
    return [
        create_list_business_entities_tool(
            business_id=business_id
        ),
        # create_search_business_entities_tool(
        #     business_id=business_id
        # ),
        create_inspect_database_tool(
            business_id=business_id
        ),
        create_inspect_collection_tool(
            business_id=business_id
        ),
        create_query_database_tool(
            business_id=business_id
        ),
        create_discover_relationships_tool(business_id=business_id),
        create_profile_collection_tool(business_id=business_id),
        create_aggregate_database_tool(business_id=business_id),
        create_aggregate_related_data_tool(business_id=business_id),
        create_traverse_relationships_tool(business_id=business_id),
        create_search_business_data_tool(business_id=business_id),
        create_find_collections_path_tool(business_id=business_id)
    ]
