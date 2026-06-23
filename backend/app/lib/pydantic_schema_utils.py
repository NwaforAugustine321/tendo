"""Pydantic model to JSON schema utilities.

Generates sanitized JSON schema descriptions from Pydantic models,
suitable for use with LLMs and structured output.
Based on CrewAI's pydantic_schema_utils.
"""

import json
from copy import deepcopy
from typing import Any, Literal, TypedDict

from pydantic import BaseModel


class JsonSchemaInfo(TypedDict):
    """Inner structure for JSON schema metadata."""
    name: str
    strict: Literal[True]
    schema: dict[str, Any]


class ModelDescription(TypedDict):
    """Return type for generate_model_description."""
    type: Literal["json_schema"]
    json_schema: JsonSchemaInfo


def resolve_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Recursively resolve all local $refs in the given JSON Schema using $defs."""
    defs = schema.get("$defs", {})
    schema_copy = deepcopy(schema)
    expanding: set[str] = set()

    def _resolve(node: Any) -> Any:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                def_name = ref.replace("#/$defs/", "")
                if def_name not in defs:
                    return node
                if def_name in expanding:
                    return {"type": defs[def_name].get("type", "object")}
                expanding.add(def_name)
                try:
                    return _resolve(deepcopy(defs[def_name]))
                finally:
                    expanding.discard(def_name)
            return {k: _resolve(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_resolve(i) for i in node]
        return node

    return _resolve(schema_copy)


def force_additional_properties_false(schema: Any) -> Any:
    """Force additionalProperties=false on all object-type dicts recursively."""
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            schema["additionalProperties"] = False
            if "properties" not in schema:
                schema["properties"] = {}
            if "required" not in schema:
                schema["required"] = []
        for v in schema.values():
            force_additional_properties_false(v)
    elif isinstance(schema, list):
        for i in schema:
            force_additional_properties_false(i)
    return schema


def ensure_all_properties_required(schema: Any) -> Any:
    """Ensure all properties are in the required array."""
    if isinstance(schema, dict):
        if schema.get("type") == "object" and "properties" in schema:
            schema["required"] = list(schema["properties"].keys())
        for v in schema.values():
            ensure_all_properties_required(v)
    elif isinstance(schema, list):
        for i in schema:
            ensure_all_properties_required(i)
    return schema


def generate_model_description(model: type[BaseModel]) -> ModelDescription:
    """Generate JSON schema description of a Pydantic model.

    Takes a Pydantic model class and returns its JSON schema with
    all refs resolved, additionalProperties set to false, and all
    properties marked as required.

    Args:
        model: A Pydantic model class.

    Returns:
        A ModelDescription with JSON schema representation.
    """
    json_schema = model.model_json_schema(ref_template="#/$defs/{model}")
    json_schema = force_additional_properties_false(json_schema)
    json_schema = resolve_refs(json_schema)
    json_schema.pop("$defs", None)
    json_schema = ensure_all_properties_required(json_schema)

    return {
        "type": "json_schema",
        "json_schema": {
            "name": model.__name__,
            "strict": True,
            "schema": json_schema,
        },
    }
