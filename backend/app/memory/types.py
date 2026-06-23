"""Data types for the memory system."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MemoryRecord(BaseModel):
    """A single memory entry stored in the memory system."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the memory record.",
    )
    content: str = Field(description="The textual content of the memory.")
    scope: str = Field(
        default="/",
        description="Hierarchical path organizing the memory.",
    )
    categories: list[str] = Field(
        default_factory=list,
        description="Categories or tags for the memory.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata associated with the memory.",
    )
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Importance score from 0.0 to 1.0.",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the memory was created.",
    )
    last_accessed: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the memory was last accessed.",
    )
    embedding: list[float] | None = Field(
        default=None,
        exclude=True,
        repr=False,
        description="Vector embedding for semantic search.",
    )
    source: str | None = Field(
        default=None,
        description="Origin of this memory (e.g. user ID, session ID).",
    )
    private: bool = Field(
        default=False,
        description="If True, only visible to recall from the same source.",
    )


class MemoryMatch(BaseModel):
    """A memory record with relevance score from a recall operation."""

    record: MemoryRecord = Field(description="The matched memory record.")
    score: float = Field(description="Combined relevance score.")
    match_reasons: list[str] = Field(
        default_factory=list,
        description="Reasons for the match.",
    )

    def format(self) -> str:
        """Format this match as a human-readable string."""
        lines = [f"- (score={self.score:.2f}) {self.record.content}"]
        if self.record.categories:
            lines.append(f"  categories: {', '.join(self.record.categories)}")
        return "\n".join(lines)


class MemoryConfig(BaseModel):
    """Configuration for memory scoring and recall behavior."""

    recency_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    semantic_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    importance_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    recency_half_life_days: int = Field(default=30, ge=1)
    consolidation_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    consolidation_limit: int = Field(default=5, ge=1)
    default_importance: float = Field(default=0.5, ge=0.0, le=1.0)


def compute_composite_score(
    record: MemoryRecord,
    semantic_score: float,
    config: MemoryConfig,
) -> tuple[float, list[str]]:
    """Compute weighted composite relevance score.

    composite = w_semantic * semantic + w_recency * decay + w_importance * importance
    where decay = 0.5^(age_days / half_life_days).
    """
    age_seconds = (datetime.utcnow() - record.created_at).total_seconds()
    age_days = max(age_seconds / 86400.0, 0.0)
    decay = 0.5 ** (age_days / config.recency_half_life_days)

    composite = (
        config.semantic_weight * semantic_score
        + config.recency_weight * decay
        + config.importance_weight * record.importance
    )

    reasons: list[str] = ["semantic"]
    if decay > 0.5:
        reasons.append("recency")
    if record.importance > 0.5:
        reasons.append("importance")

    return composite, reasons
