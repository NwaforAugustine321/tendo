from __future__ import annotations

from .memory_provider import MemoryProvider
from .lancedb import LanceMemoryStore
from .default_reflection import DefaultMemoryReflection


def create_memory_provider(namespace: str, scopes: list[str] | None = None) -> MemoryProvider:
    """
    Create the default memory provider.
    """

    return MemoryProvider(
        store=LanceMemoryStore(namespace=namespace, scopes=scopes),
        reflection=DefaultMemoryReflection(),
    )
