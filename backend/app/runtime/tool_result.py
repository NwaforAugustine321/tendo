"""Unified tool result model — all tools return this structure."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Standard result format returned by all tools.

    The agent runtime extracts these fields and builds the appropriate
    LLM message (text content + image attachments).
    """

    content: str = Field(default="", description="Text content of the tool result")
    metadata: dict = Field(default_factory=dict, description="Structured metadata about the result")
    images: list[str] = Field(default_factory=list, description="Base64-encoded images or image URLs")
    videos: list[str] = Field(default_factory=list, description="Video URLs (reserved for future use)")
    audios: list[str] = Field(default_factory=list, description="Audio URLs (reserved for future use)")
