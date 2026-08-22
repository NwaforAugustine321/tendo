from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


SnapType = Literal[
    "recommendation",
    "attention",
    "warning",
    "opportunity"
]

SnapPriority = Literal[
    "low",
    "medium",
    "high",
    "critical",
]


@dataclass(
    slots=True,
    frozen=True,
)
class SnapModel:

    type: SnapType

    priority: SnapPriority

    confidence: float

    title: str

    message: str

    why_it_matters: str

    action: str


SnapStatus = Literal[
    "active",
    "completed",
]


@dataclass(
    slots=True,
    frozen=True,
)
class SnapRecord:

    snap_id: str

    business_id: str

    snap: SnapModel

    status: SnapStatus = "active"
