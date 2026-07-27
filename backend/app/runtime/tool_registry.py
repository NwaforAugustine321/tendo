"""Tool Registry — builds a name→tool map from a list of tools."""

from typing import Any


def build_tool_registry(tools: list[Any]) -> dict[str, Any]:
    return {t.name: t for t in tools}
