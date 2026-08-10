from __future__ import annotations

from .provider import MemoryProvider
from .lancedb import LanceMemoryStore
from .default_reflection import DefaultMemoryReflection


def create_memory_provider(namespace: str) -> MemoryProvider:
    """
    Create the default memory provider.
    """

    return MemoryProvider(
        store=LanceMemoryStore(namespace=namespace),
        reflection=DefaultMemoryReflection(),
    )
