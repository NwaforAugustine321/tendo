from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LearningContext:
    """
    Context supplied to the learning agent for one learning cycle.
    """

    business_id: str
    events: list[dict[str, Any]]


@dataclass(frozen=True)
class LearningResult:
    knowledge: list[str] = field(
        default_factory=list,
    )
