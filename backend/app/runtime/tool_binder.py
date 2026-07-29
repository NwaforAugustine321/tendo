

from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ToolBinder:
    """Resolves ToolReference entries to concrete tool instances at execution time."""

    def __init__(self, tool_registry: dict[str, Any] | None = None) -> None:
        self._registry: dict[str, Any] = tool_registry or {}
        self._bound_tools: list[Any] = []

    def bind(self, tool_refs: list[Any] | None = None) -> list[Any]:
        """Resolve tool references to concrete tool callables.
        
        If tool_refs is provided, only those tools are resolved.
        If tool_refs is None or empty, all tools in the registry are bound.
        """
        bound: list[Any] = []

        if not tool_refs:
            # Bind all tools from the registry
            bound = list(self._registry.values())
        else:
            for ref in tool_refs:
                tool_id = ref.tool_id if hasattr(ref, 'tool_id') else str(ref)
                tool = self._registry.get(tool_id)
                if tool is None:
                    
                    continue
                bound.append(tool)

        self._bound_tools = bound
        return list(bound)

    async def release(self) -> None:
        """Release all bound tool references."""
        self._bound_tools = []
