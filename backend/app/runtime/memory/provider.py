from __future__ import annotations

from abc import ABC, abstractmethod

from app.runtime.agents.run_context import RunContext

from .context import MemoryContext
from .reflection import MemoryReflectionEngine
from .store import MemoryStore


class MemoryProvider(ABC):
    """
    Coordinates long-term memory for an agent.

    A MemoryProvider is responsible for:

    - retrieving memories relevant to the current run
    - reflecting over a completed run
    - persisting learned memories

    The concrete implementation composes a MemoryStore
    and a MemoryReflectionEngine.
    """

    @property
    @abstractmethod
    def store(
        self,
    ) -> MemoryStore:
        """
        The underlying persistent memory store.
        """
        ...

    @property
    @abstractmethod
    def reflection_engine(
        self,
    ) -> MemoryReflectionEngine:
        """
        The engine responsible for extracting durable
        memories from completed runs.
        """
        ...

    @abstractmethod
    async def retrieve(
        self,
        ctx: RunContext,
    ) -> MemoryContext:
        """
        Retrieve memories relevant to the current run.
        """
        ...

    @abstractmethod
    async def reflect(
        self,
        ctx: RunContext,
    ) -> None:
        """
        Reflect over the completed run and persist any
        durable memories.
        """
        ...
