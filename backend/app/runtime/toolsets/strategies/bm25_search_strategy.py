from __future__ import annotations

import re
from collections.abc import Awaitable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

if TYPE_CHECKING:
    from .tool_context import Tool, Toolset
from .strategy import (
    SearchStrategy,
    SearchItem
)


class BM25SearchStrategy(SearchStrategy):
    """
    BM25-based search strategy.

    BM25 ranks items by term frequency, inverse document frequency,
    and document length normalization.

    Field weights:
        - Tool name ............. 3
        - Description ........... 2
        - Parameters ............ 1
    """

    INDEX_KEY = "bm25"

    def __init__(
        self,
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self._k1 = k1
        self._b = b
        self._avg_dl: float = 0.0
        self._idf: dict[str, float] = {}

    def build_index(
        self,
        items: list[SearchItem],
    ) -> None:

        import math

        for item in items:

            tokens = self._tokenize(item)

            tf: dict[str, float] = {}

            for token in tokens:
                tf[token] = (
                    tf.get(token, 0.0) + 1.0
                )

            item.index_data[
                self.INDEX_KEY
            ] = {
                "tokens": tokens,
                "tf": tf,
                "dl": len(tokens),
            }

        total_dl = sum(
            item.index_data[
                self.INDEX_KEY
            ]["dl"]
            for item in items
        )

        self._avg_dl = (
            total_dl / len(items)
            if items
            else 0.0
        )

        document_count = len(items)

        document_frequency: dict[str, int] = {}

        for item in items:

            seen: set[str] = set()

            tokens = item.index_data[
                self.INDEX_KEY
            ]["tokens"]

            for token in tokens:

                if token in seen:
                    continue

                document_frequency[token] = (
                    document_frequency.get(
                        token,
                        0,
                    )
                    + 1
                )

                seen.add(token)

        self._idf = {}

        for term, frequency in (
            document_frequency.items()
        ):
            self._idf[term] = math.log(
                (
                    document_count
                    - frequency
                    + 0.5
                )
                / (
                    frequency
                    + 0.5
                )
                + 1.0,
            )

    def search(
        self,
        query: str,
        items: list[SearchItem],
        max_results: int,
    ) -> list[SearchItem]:

        if max_results <= 0:
            return []

        query_terms = (
            query
            .lower()
            .replace("_", " ")
            .split()
        )

        if not query_terms:
            return []

        scored: list[
            tuple[float, SearchItem]
        ] = []

        for item in items:

            score = self._score(
                item,
                query_terms,
            )

            if score > 0:
                scored.append(
                    (score, item),
                )

        scored.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        return [
            item
            for _, item in scored[:max_results]
        ]

    def cleanup(
        self,
    ) -> None:

        self._idf.clear()
        self._avg_dl = 0.0

    def _tokenize(
        self,
        item: SearchItem,
    ) -> list[str]:

        name_tokens = (
            item.name
            .lower()
            .replace("_", " ")
            .split()
        )

        description_tokens = (
            item.description
            .lower()
            .split()
        )

        parameter_tokens: list[str] = []

        for key, value in item.parameters.items():

            parameter_tokens.extend(
                key
                .lower()
                .replace("_", " ")
                .split(),
            )

            parameter_tokens.extend(
                value.lower().split(),
            )

        return (
            name_tokens * 3
            + description_tokens * 2
            + parameter_tokens
        )

    def _score(
        self,
        item: SearchItem,
        query_terms: list[str],
    ) -> float:

        idx = item.index_data.get(
            self.INDEX_KEY,
        )

        if idx is None:

            self.build_index(
                [item],
            )

            idx = item.index_data[
                self.INDEX_KEY
            ]

        tf = idx["tf"]
        dl = idx["dl"]

        score = 0.0

        for term in query_terms:

            idf = self._idf.get(term)

            if idf is None:
                continue

            term_freq = tf.get(
                term,
                0.0,
            )

            numerator = (
                term_freq
                * (self._k1 + 1.0)
            )

            denominator = (
                term_freq
                + self._k1
                * (
                    1.0
                    - self._b
                    + self._b
                    * dl
                    / self._avg_dl
                    if self._avg_dl > 0
                    else 1.0
                )
            )

            score += (
                idf
                * numerator
                / denominator
            )

        return score
