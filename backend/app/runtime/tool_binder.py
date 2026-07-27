

from __future__ import annotations
import logging
from typing import Any
from app.contexts.models import ToolReference

logger = logging.getLogger(__name__)


class ToolBinder:
    """Resolves ToolReference entries to concrete tool instances at execution time."""

    def __init__(self, tool_registry: dict[str, Any] | None = None) -> None:
        self._registry: dict[str, Any] = tool_registry or {}
        self._bound_tools: list[Any] = []

    async def bind(self, tool_refs: list[ToolReference]) -> list[Any]:
        """Resolve tool references to concrete tool callables. Excludes unavailable tools."""
        bound: list[Any] = []

        for ref in tool_refs:
            tool = self._registry.get(ref.tool_id)
            if tool is None:
                logger.info("Tool '%s' unavailable — excluded from binding.", ref.tool_id)
                continue
            bound.append(tool)

        self._bound_tools = bound
        return list(bound)

    async def release(self) -> None:
        """Release all bound tool references."""
        self._bound_tools = []
