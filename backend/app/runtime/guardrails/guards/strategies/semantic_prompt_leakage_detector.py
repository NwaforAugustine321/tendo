from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import lancedb
from lancedb.pydantic import LanceModel, Vector

from app.runtime.embeddings.client import (
    get_embedding_client,
)
from app.runtime.embeddings.provider import (
    EmbeddingProvider,
)

from .strategy import PromptLeakageDetectionStrategy


def create_prompt_schema(
    dimension: int,
) -> type[LanceModel]:

    class PromptRecord(LanceModel):

        id: str
        prompt_id: str
        source: str
        content: str
        vector: Vector(dimension)

    return PromptRecord


class SemanticLeakageSearchStrategy(
    PromptLeakageDetectionStrategy,
):

    def __init__(
        self,
        *,
        db: lancedb.DBConnection | None = None,
        namespace: str = "internal/prompts",
        table_name: str = "prompts",
        uri: str | Path = "./data/internal/prompts",
        embeddings: EmbeddingProvider | None = None,
        threshold: float = 0.20,
    ) -> None:

        self._embeddings = (
            embeddings
            or get_embedding_client()
        )

        self._db = (
            db
            or lancedb.connect(
                str(
                    Path(uri) / namespace,
                ),
            )
        )

        self._schema = create_prompt_schema(
            self._embeddings.dimension,
        )

        self._table = (
            self._get_or_create_table(
                table_name,
            )
        )

        self._threshold = threshold

        self._pending: list[dict] = []
        self._pending_lock = asyncio.Lock()

    def queue_index(
        self,
        prompts: list[dict],
    ) -> None:
        """
        Register prompts for indexing from synchronous code.

        Indexing needs to embed the content, which is async, so callers
        that cannot await (such as constructors) queue the prompts here
        and the index is built on first search.
        """

        if prompts:
            self._pending.extend(
                prompts,
            )

    async def flush_index(self) -> None:
        """
        Index anything queued. Safe to call repeatedly and concurrently;
        build_index skips prompts that are already stored.
        """

        if not self._pending:
            return

        async with self._pending_lock:

            if not self._pending:
                return

            pending, self._pending = self._pending, []

            try:
                await self.build_index(
                    pending,
                )
            except Exception:
                # Keep the prompts so a later search can retry.
                self._pending = pending + self._pending
                raise

    def _get_or_create_table(
        self,
        table_name: str,
    ):

        if table_name in self._db.table_names():
            return self._db.open_table(
                table_name,
            )

        return self._db.create_table(
            table_name,
            schema=self._schema,
        )

    async def build_index(
        self,
        prompts: list[{
            id: str,
            content: str,
            source: str
        }],
    ) -> None:

        if not prompts:
            return

        unique_prompts: dict[str, dict] = {}

        for prompt in prompts:
            prompt_id = self._prompt_id(prompt)
            unique_prompts[prompt_id] = prompt

        if not unique_prompts:
            return

        existing_ids = self._existing_ids(
            list(unique_prompts.keys()),
        )

        prompts_to_embed = [
            prompt
            for prompt_id, prompt in unique_prompts.items()
            if prompt_id not in existing_ids
        ]

        if not prompts_to_embed:
            return

        texts = [
            prompt["content"]
            for prompt in prompts_to_embed
        ]

        vectors = await (
            self._embeddings.embed_documents(
                texts,
            )
        )

        rows = []

        for prompt, vector in zip(
            prompts_to_embed,
            vectors,
        ):
            rows.append(
                self._schema(
                    id=self._prompt_id(prompt),
                    prompt_id=prompt["id"],
                    source=prompt["source"],
                    content=prompt["content"],
                    vector=vector,
                ),
            )

        if rows:
            self._table.add(rows)

    def _existing_ids(
        self,
        ids: list[str],
    ) -> set[str]:

        if not ids:
            return set()

        existing: set[str] = set()

        for prompt_id in ids:
            rows = (
                self._table
                .search()
                .where(
                    f"id = '{prompt_id}'",
                )
                .limit(1)
                .to_list()
            )

            if rows:
                existing.add(prompt_id)

        return existing

    async def search(
        self,
        response: str,
        max_results: int = 5,
    ) -> list[dict]:

        if (
            not response
            or not response.strip()
            or max_results <= 0
        ):
            return []

        await self.flush_index()

        vector = await (
            self._embeddings.embed(
                response,
            )
        )

        rows = (
            self._table
            .search(vector)
            .metric("cosine")
            .limit(max_results)
            .to_list()
        )

        results: list[dict] = []

        for row in rows:

            distance = row.get(
                "_distance",
            )

            if distance is None:
                continue

            results.append(
                {
                    "id": row["id"],
                    "prompt_id": row["prompt_id"],
                    "source": row["source"],
                    "content": row["content"],
                    "distance": float(distance),
                },
            )

        return results

    async def detect_match(
        self,
        response: str,
        *,
        threshold: float | None = None,
    ) -> dict | None:

        if not response or not response.strip():
            return None

        threshold = (
            self._threshold
            if threshold is None
            else threshold
        )

        results = await self.search(
            response,
            max_results=1,
        )

        if not results:
            return None

        result = results[0]

        if result["distance"] > threshold:
            return None

        return result

    async def detect(
        self,
        text: str,
    ) -> dict | None:

        match = await self.detect_match(
            text,
        )

        if match is None:
            return None

        return {
            "strategy": "semantic",
            "prompt_id": match["prompt_id"],
            "source": match["source"],
            "content": match["content"],
            "distance": match["distance"],
        }

    async def is_leakage(
        self,
        response: str,
        *,
        threshold: float | None = None,
    ) -> bool:

        return (
            await self.detect_match(
                response,
                threshold=threshold,
            )
        ) is not None

    @staticmethod
    def _prompt_id(
        prompt: dict,
    ) -> str:

        content = (
            f"{prompt['id']}|"
            f"{prompt['source']}|"
            f"{prompt['content']}"
        )

        return hashlib.sha256(
            content.encode("utf-8"),
        ).hexdigest()
