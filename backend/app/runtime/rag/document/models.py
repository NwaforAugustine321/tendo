from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RecordContentInput:
    """
    Input source for content processing.
    """

    content: str | None = None

    content_type: str | None = None


@dataclass(slots=True)
class ProcessingMetadata:
    """
    Metadata generated during content processing.
    """

    title: str = ""

    summary: str = ""

    suggested_questions: list[str] = field(
        default_factory=list,
    )


@dataclass(slots=True)
class ProcessingResult:
    """
    Result returned by the content processor.
    """

    success: bool

    entries: list[Any] = field(
        default_factory=list,
    )

    documents: int = 0

    chunks: int = 0

    metadata: ProcessingMetadata = field(
        default_factory=ProcessingMetadata,
    )

    error: str | None = None
