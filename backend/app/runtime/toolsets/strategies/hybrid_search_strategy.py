from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from .strategy import (
    SearchItem,
    SearchStrategy,
)

if TYPE_CHECKING:
    from .bm25_search_strategy import (
        BM25SearchStrategy,
    )
    from .sematic_search_strategy import (
        SemanticSearchStrategy,
    )


class HybridSearchStrategy(
    SearchStrategy,
):
    """
    Hybrid search strategy combining:

    - BM25 lexical search
    - Semantic vector search

    Results are combined using
    Reciprocal Rank Fusion (RRF).
    """

    def __init__(
        self,
        *,
        bm25: BM25SearchStrategy,
        vector: SemanticSearchStrategy,
        rrf_k: int = 60,
        candidate_limit: int = 10,
    ) -> None:

        if rrf_k <= 0:
            raise ValueError(
                "rrf_k must be greater than zero.",
            )

        if candidate_limit <= 0:
            raise ValueError(
                "candidate_limit must be greater than zero.",
            )

        self._bm25 = bm25
        self._vector = vector
        self._rrf_k = rrf_k
        self._candidate_limit = candidate_limit

    async def build_index(
        self,
        items: list[SearchItem],
    ) -> None:
        """
        Build both lexical and semantic indexes.
        """

        if not items:
            return

        self._bm25.build_index(
            items,
        )

        await self._vector.build_index(
            items,
        )

    async def search(
        self,
        query: str,
        items: list[SearchItem],
        max_results: int,
    ) -> list[SearchItem]:
        """
        Search using BM25 and semantic search,
        then combine the rankings using RRF.
        """

        if (
            not query.strip()
            or not items
            or max_results <= 0
        ):
            return []

        candidate_limit = max(
            self._candidate_limit,
            max_results,
        )

        #
        # Lexical search.
        #
        bm25_results = self._bm25.search(
            query=query,
            items=items,
            max_results=candidate_limit,
        )

        #
        # Semantic search.
        #
        semantic_results = await (
            self._vector.search(
                query=query,
                items=items,
                max_results=candidate_limit,
            )
        )

        #
        # Combine rankings using RRF.
        #
        scores: dict[
            int,
            float,
        ] = defaultdict(float)

        item_map: dict[
            int,
            SearchItem,
        ] = {}

        self._add_rankings(
            results=bm25_results,
            scores=scores,
            item_map=item_map,
        )

        self._add_rankings(
            results=semantic_results,
            scores=scores,
            item_map=item_map,
        )

        #
        # Highest RRF score first.
        #
        ranked = sorted(
            scores.items(),
            key=lambda entry: entry[1],
            reverse=True,
        )

        return [
            item_map[item_id]
            for item_id, _ in ranked[
                :max_results
            ]
        ]

    def cleanup(
        self,
    ) -> None:
        """
        Clean up both search strategies.
        """

        self._bm25.cleanup()
        self._vector.cleanup()

    def _add_rankings(
        self,
        *,
        results: list[SearchItem],
        scores: dict[int, float],
        item_map: dict[int, SearchItem],
    ) -> None:
        """
        Add a ranked result list to the RRF scores.
        """

        for rank, item in enumerate(
            results,
            start=1,
        ):

            item_id = id(item)

            item_map[item_id] = item

            scores[item_id] += (
                1.0
                / (
                    self._rrf_k
                    + rank
                )
            )
