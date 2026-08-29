from __future__ import annotations

import hashlib
import json
from pathlib import Path

import lancedb
from lancedb.pydantic import LanceModel, Vector

from app.runtime.embeddings.client import (
    get_embedding_client,
)
from app.runtime.embeddings.provider import (
    EmbeddingProvider,
)

from .strategy import (
    SearchItem,
    SearchStrategy,
)


def create_tool_schema(
    dimension: int,
) -> type[LanceModel]:
    """
    Create the LanceDB schema for tool search.
    """

    class ToolRecord(LanceModel):
        id: str
        name: str
        description: str
        parameters: str
        vector: Vector(dimension)

    return ToolRecord


class SemanticSearchStrategy(
    SearchStrategy,
):
    """
    Semantic search strategy backed by LanceDB.

    Tool information is embedded and stored in LanceDB.
    Search returns the original SearchItem instances.
    """

    def __init__(
        self,
        *,
        db: lancedb.DBConnection | None = None,
        namespace: str = "tools",
        table_name: str = "tools",
        uri: str | Path = "./data/tools",
        embeddings: EmbeddingProvider | None = None,
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

        self._schema = create_tool_schema(
            self._embeddings.dimension,
        )

        self._table = (
            self._get_or_create_table(
                table_name,
            )
        )

        #
        # Maps LanceDB records back to the
        # current SearchItem instances.
        #
        self._items: dict[
            str,
            SearchItem,
        ] = {}

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
        items: list[SearchItem],
    ) -> None:
        """
        Build or update the semantic tool index.
        """

        if not items:
            return

        texts = [
            self._build_search_text(item)
            for item in items
        ]

        vectors = await (
            self._embeddings.embed_documents(
                texts,
            )
        )

        rows = []

        for item, vector in zip(
            items,
            vectors,
        ):

            item_id = self._item_id(
                item,
            )

            self._items[item_id] = item

            rows.append(
                self._schema(
                    id=item_id,
                    name=item.name,
                    description=item.description,
                    parameters=json.dumps(
                        item.parameters,
                    ),
                    vector=vector,
                ),
            )

        #
        # Replace existing records with
        # the same IDs instead of creating
        # duplicates.
        #
        self._table.merge_insert(
            "id",
        ).when_matched_update_all(
        ).when_not_matched_insert_all(
        ).execute(
            rows,
        )

    async def search(
        self,
        query: str,
        items: list[SearchItem],
        max_results: int,
    ) -> list[SearchItem]:

        if (
            not query.strip()
            or max_results <= 0
        ):
            return []

        #
        # Keep the mapping synchronized with
        # the current tool registry.
        #
        for item in items:

            self._items[
                self._item_id(item)
            ] = item

        vector = await (
            self._embeddings.embed(
                query,
            )
        )

        rows = (
            self._table
            .search(vector)
            .metric("cosine")
            .limit(max_results)
            .to_list()
        )

        results: list[SearchItem] = []

        for row in rows:

            item = self._items.get(
                row["id"],
            )

            if item is None:
                continue

            #
            # Only return tools that are
            # currently available.
            #
            if item not in items:
                continue

            results.append(
                item,
            )

        return results

    def cleanup(
        self,
    ) -> None:
        """
        Clear the in-memory SearchItem mapping.

        The persistent LanceDB index remains intact.
        """

        self._items.clear()

    @staticmethod
    def _build_search_text(
        item: SearchItem,
    ) -> str:

        parameters = " ".join(
            f"{key}: {value}"
            for key, value
            in item.parameters.items()
        )

        return (
            f"Tool: {item.name}\n"
            f"Description: {item.description}\n"
            f"Parameters: {parameters}"
        )

    @staticmethod
    def _item_id(
        item: SearchItem,
    ) -> str:

        content = (
            f"{item.name}|"
            f"{item.description}|"
            f"{json.dumps(item.parameters, sort_keys=True)}"
        )

        return hashlib.sha256(
            content.encode("utf-8"),
        ).hexdigest()
