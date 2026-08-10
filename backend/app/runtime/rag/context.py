from __future__ import annotations

from dataclasses import dataclass, field

from .models import RAGDocument


@dataclass(slots=True)
class RAGContext:
    """
    Documents retrieved for the current run.
    """

    documents: list[RAGDocument] = field(
        default_factory=list,
    )

    @property
    def empty(
        self,
    ) -> bool:

        return len(self.documents) == 0
