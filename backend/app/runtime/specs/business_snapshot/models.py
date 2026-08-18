"""Business Snapshot models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SnapshotStory(BaseModel):
    """A single narrative story in the business snapshot."""
    title: str = Field(description="Brief headline")
    narrative: str = Field(description="Natural language explanation")
    area: str = Field(default="general", description="Business area: finance, customers, operations, sales, inventory, general")
    sentiment: str = Field(default="neutral", description="positive, neutral, or attention_needed")


class SnapshotRecommendation(BaseModel):
    """An actionable recommendation for the business owner."""
    action: str = Field(description="What to do")
    reason: str = Field(description="Why it matters")
    priority: str = Field(default="medium", description="high, medium, or low")


class BusinessSnapshot(BaseModel):
    """The current business narrative shown on the dashboard."""
    business_id: str = ""
    stories: list[SnapshotStory] = Field(default_factory=list)
    recommendations: list[SnapshotRecommendation] = Field(default_factory=list)
