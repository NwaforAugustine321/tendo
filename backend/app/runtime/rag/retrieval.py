from __future__ import annotations

from abc import ABC, abstractmethod

from app.runtime.agents.run_context import RunContext


class RetrievalEngine(ABC):
    """
    Builds the search query for retrieving knowledge.
    """

    @abstractmethod
    def build_query(
        self,
        ctx: RunContext,
    ) -> str:
        ...
