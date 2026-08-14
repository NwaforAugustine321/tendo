from __future__ import annotations

import re
from collections.abc import Awaitable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

if TYPE_CHECKING:
    from .tool_context import Tool, Toolset


@dataclass(slots=True)
class SearchItem:
    """One searchable representation of a tool."""

    source: Tool | Toolset
    name: str
    description: str
    parameters: dict[str, str] = field(default_factory=dict)

    index_data: dict[str, Any] = field(
        default_factory=dict,
        repr=False,
    )


class SearchStrategy(Protocol):
    """Defines the contract every search strategy must implement."""

    def build_index(
        self,
        items: list[SearchItem],
    ) -> None | Awaitable[None]:
        ...

    def search(
        self,
        query: str,
        items: list[SearchItem],
        max_results: int,
    ) -> list[SearchItem] | Awaitable[list[SearchItem]]:
        ...

    def cleanup(
        self,
    ) -> None | Awaitable[None]:
        ...
