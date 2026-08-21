from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SnapType(StrEnum):
    RECOMMENDATION = "recommendation"
    ATTENTION = "attention"
    ANOMALY = "anomaly"
    RISK = "risk"
    OPPORTUNITY = "opportunity"
    TREND = "trend"


class SnapPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class Snap:
    type: SnapType
    priority: SnapPriority
    confidence: float
    title: str
    message: str
    why_it_matters: str
    action: str

    def __post_init__(self) -> None:

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "confidence must be between 0.0 and 1.0.",
            )

        if not self.title.strip():
            raise ValueError(
                "title cannot be empty.",
            )

        if not self.message.strip():
            raise ValueError(
                "message cannot be empty.",
            )

        if not self.why_it_matters.strip():
            raise ValueError(
                "why_it_matters cannot be empty.",
            )

        if not self.action.strip():
            raise ValueError(
                "action cannot be empty.",
            )

        if len(self.title) > 80:
            raise ValueError(
                "title cannot exceed 80 characters.",
            )

        if len(self.message) > 240:
            raise ValueError(
                "message cannot exceed 240 characters.",
            )

        if len(self.why_it_matters) > 180:
            raise ValueError(
                "why_it_matters cannot exceed 180 characters.",
            )

        if len(self.action) > 160:
            raise ValueError(
                "action cannot exceed 160 characters.",
            )
