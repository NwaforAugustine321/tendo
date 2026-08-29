from __future__ import annotations

from abc import ABC, abstractmethod

from .context import MemoryContext
from .reflection import MemoryReflection


class MemoryStore(ABC):
    """
    Persistent storage backend for long-term memory.

    MemoryStore is responsible only for persisting and retrieving
    memories. It has no knowledge of agents, conversations, or
    RunContext.
    """

    @abstractmethod
    async def retrieve(
        self,
        *,
        query: str,
        limit: int = 10,
    ) -> MemoryContext:
        """
        Retrieve memories relevant to the supplied query.
        """
        ...

    @abstractmethod
    async def save(
        self,
        *,
        reflection: MemoryReflection,
    ) -> None:
        """
        Persist the memory operations produced by reflection.
        """
        ...

    @abstractmethod
    async def delete(
        self,
        *,
        memory_id: str,
    ) -> None:
        """
        Delete a memory by its unique identifier.
        """
        ...
