import json
from copy import deepcopy
from typing import Any

from pydantic import BaseModel, TypeAdapter


def resolve_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Inline all local $refs so nested models are readable
    without needing the $defs section.
    """

    defs = schema.get("$defs", {})
    expanding: set[str] = set()

    def _resolve(node: Any) -> Any:
        if isinstance(node, dict):
            ref = node.get("$ref")

            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                name = ref.removeprefix("#/$defs/")

                if name not in defs:
                    return node

                # Self-referencing model: stop recursing.
                if name in expanding:
                    return {
                        "type": defs[name].get("type", "object"),
                    }

                expanding.add(name)
                try:
                    return _resolve(deepcopy(defs[name]))
                finally:
                    expanding.discard(name)

            return {k: _resolve(v) for k, v in node.items()}

        if isinstance(node, list):
            return [_resolve(item) for item in node]

        return node

    resolved = _resolve(deepcopy(schema))
    resolved.pop("$defs", None)

    return resolved


def pydantic_to_string(model: Any) -> str:
    """
    Render any type annotation's JSON schema as a string,
    for embedding in a prompt.

    Accepts a BaseModel subclass, a TypeAdapter, or any plain
    annotation such as list[Model], Model | None, dict or str.

    Returns "{}" when a schema cannot be produced.
    """

    ref_template = "#/$defs/{model}"

    try:
        if isinstance(model, TypeAdapter):
            schema = model.json_schema(
                ref_template=ref_template,
            )

        elif isinstance(model, type) and issubclass(model, BaseModel):
            schema = model.model_json_schema(
                ref_template=ref_template,
            )

        else:
            # Covers list[Model], unions, and bare types.
            schema = TypeAdapter(model).json_schema(
                ref_template=ref_template,
            )

    except Exception:
        return "{}"

    return json.dumps(
        resolve_refs(schema),
        indent=2,
    )
