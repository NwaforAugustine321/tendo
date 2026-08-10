from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RAGDocument:
    """
    One knowledge document stored in RAG.
    """

    id: str

    content: str

    title: str = ""

    source: str = ""

    score: float = 1.0

    parent_id: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )
