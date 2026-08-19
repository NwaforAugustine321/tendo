from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import lancedb

from app.runtime.memory.lancedb import LanceMemoryStore

from .interface import LearningKnowledge


class LearningKnowledgeMemory(
    LanceMemoryStore,
    LearningKnowledge,
):
    DUPLICATE_DISTANCE = 0.08

    def __init__(
        self,
        *,
        db: lancedb.DBConnection | None = None,
        namespace: str,
        table_name: str = "knowledge",
        uri: str | Path = "./data/memory",
        scopes: list[str] | None = None,
    ) -> None:

        super().__init__(
            db=db,
            namespace=namespace,
            table_name=table_name,
            uri=uri,
            scopes=scopes,
            ignore_threshold=True,
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

        vectors = await self._embeddings.embed_documents(
            knowledge,
        )

        entries = []

        for text, vector in zip(
            knowledge,
            vectors,
        ):

            if self._is_duplicate(
                vector,
            ):
                continue

            entries.append(
                self._schema(
                    id=str(uuid4()),
                    text=text,
                    category="knowledge",
                    scopes=self._scopes,
                    metadata=json.dumps({}),
                    created_at=datetime.now(UTC),
                    vector=vector,
                )
            )

        if entries:
            self._table.add(
                entries,
            )
