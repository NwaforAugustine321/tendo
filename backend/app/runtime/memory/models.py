from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MemoryEntry:
    """
    One retrieved memory.
    """

    id: str

    text: str

    score: float = 0.0

    category: str = "general"

    source: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )
