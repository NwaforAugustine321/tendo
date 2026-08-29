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


class KeywordSearchStrategy(SearchStrategy):
    """
    Simple keyword-based search.

    Scoring:
        - Tool name ............. +3
        - Description ........... +2
        - Parameters ............ +1
    """

    INDEX_KEY = "keyword"

    def build_index(
        self,
        items: list[SearchItem],
    ) -> None:
        """Pre-compute searchable text for every SearchItem."""

        for item in items:
            item.index_data[
                self.INDEX_KEY
            ] = {
                "name": item.name.lower(),
                "description": item.description.lower(),
                "parameters": " ".join(
                    f"{key} {value}"
                    for key, value in item.parameters.items()
                ).lower(),
            }

    def search(
        self,
        query: str,
        items: list[SearchItem],
        max_results: int,
    ) -> list[SearchItem]:
        """Return the highest scoring SearchItems."""

        if max_results <= 0:
            return []

        keywords = list(
            set(
                query.lower().split(),
            ),
        )

        if not keywords:
            return []

        scored: list[
            tuple[float, SearchItem]
        ] = []

        for item in items:

            score = self._score(
                item,
                keywords,
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
        """Remove the keyword index."""

        # The index belongs to SearchItems, so there is
        # no strategy-level state to clean up.
        pass

    def _score(
        self,
        item: SearchItem,
        keywords: list[str],
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

        score = 0.0

        for keyword in keywords:

            try:
                pattern = re.compile(
                    keyword,
                )
            except re.error:
                pattern = re.compile(
                    re.escape(keyword),
                )

            if pattern.search(
                idx["name"],
            ):
                score += 3.0

            if pattern.search(
                idx["description"],
            ):
                score += 2.0

            if pattern.search(
                idx["parameters"],
            ):
                score += 1.0

        return score
