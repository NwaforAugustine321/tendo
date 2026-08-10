from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.runtime.agents.run_context import RunContext

from .models import MemoryEntry


@dataclass(slots=True)
class MemoryReflection:
    """
    Durable memories extracted from a completed run.

    The reflection engine is responsible only for
    identifying memories. It does not decide whether
    they should be created, updated, merged, or ignored.
    """

    entries: list[MemoryEntry] = field(
        default_factory=list,
    )

    @property
    def empty(
        self,
    ) -> bool:

        return len(self.entries) == 0


class MemoryReflectionEngine(ABC):
    """
    Learns durable memories from a completed run.
    """

    @abstractmethod
    async def reflect(
        self,
        ctx: RunContext,
    ) -> MemoryReflection:
        """
        Analyze the completed run and return the
        durable memories that were discovered.
        """
        ...
