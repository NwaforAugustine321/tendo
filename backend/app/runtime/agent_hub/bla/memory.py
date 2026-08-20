from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import lancedb

from app.runtime.memory.memory_provider import MemoryProvider
from app.runtime.memory.models import MemoryEntry
from app.runtime.memory.reflection import MemoryReflection
from app.runtime.memory.lancedb import LanceMemoryStore

from .interface import LearningKnowledge


class LearningKnowledgeMemory(
    MemoryProvider,
    LearningKnowledge,
):

    def __init__(
        self,
        *,
        db: lancedb.DBConnection | None = None,
        namespace: str,
        table_name: str = "business_knowledge",
        uri: str | Path = "./data/memory",
        scopes: list[str] | None = None,
    ) -> None:

        super().__init__(
            store=LanceMemoryStore(
                db=db,
                namespace=namespace,
                table_name=table_name,
                uri=uri,
                scopes=scopes,
                ignore_threshold=True,
            )
        )

    async def save_knowledge(
        self,
        *,
        knowledge: list[str],
    ) -> None:

        if not isinstance(
            knowledge,
            list,
        ):
            raise TypeError(
                "knowledge must be a list of strings.",
            )

        knowledge = [
            item.strip()
            for item in knowledge
            if isinstance(item, str)
            and item.strip()
        ]

        if not knowledge:
            return

        entries = [
            MemoryEntry(
                id=str(uuid4()),
                text=text,
                category="knowledge",
            )
            for text in knowledge
        ]

        reflection = MemoryReflection(entries=entries)

        await self._store.save(
            reflection=reflection,
        )
