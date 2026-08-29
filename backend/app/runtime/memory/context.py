from __future__ import annotations

from dataclasses import dataclass, field

from .models import MemoryEntry


@dataclass(slots=True)
class MemoryContext:
    """
    Retrieved memories for one run.
    """

    entries: list[MemoryEntry] = field(
        default_factory=list,
    )

    @property
    def empty(
        self,
    ) -> bool:

        return len(self.entries) == 0
