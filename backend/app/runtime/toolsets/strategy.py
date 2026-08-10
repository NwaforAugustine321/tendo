from __future__ import annotations

import re
from collections.abc import Awaitable
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from app.toolsets.tool_context import Tool, Toolset

# ---------------------------------------------------------------------------
# SearchItem / SearchStrategy / KeywordSearchStrategy / BM25SearchStrategy
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SearchItem:
    """One searchable representation of a tool."""

    source: Tool | Toolset
    name: str
    description: str
    parameters: dict[str, str] = field(default_factory=dict)
    index_data: Any = field(default=None, repr=False)


class SearchStrategy(Protocol):
    """Defines the contract every search strategy must implement."""

    def build_index(
        self,
        items: list[SearchItem],
    ) -> None | Awaitable[None]:
        ...

    def search(
        self,
        query: str,
        items: list[SearchItem],
        max_results: int,
    ) -> list[SearchItem] | Awaitable[list[SearchItem]]:
        ...

    def cleanup(
        self,
    ) -> None | Awaitable[None]:
        ...


class KeywordSearchStrategy:
    """
    Simple keyword-based search.

    Scoring:
        - Tool name ............. +3
        - Description ........... +2
        - Parameters ............ +1
    """

    def build_index(self, items: list[SearchItem]) -> None:
        """Pre-compute searchable text for every SearchItem."""
        for item in items:
            item.index_data = {
                "name": item.name.lower(),
                "description": item.description.lower(),
                "parameters": " ".join(
                    f"{k} {v}" for k, v in item.parameters.items()
                ).lower(),
            }

    def search(
        self,
        query: str,
        items: list[SearchItem],
        max_results: int,
    ) -> list[SearchItem]:
        """Return the highest scoring SearchItems."""
        keywords = list(set(query.lower().split()))

        if not keywords:
            return []

        scored: list[tuple[float, SearchItem]] = []

        for item in items:
            score = self._score(item, keywords)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:max_results]]

    def cleanup(self) -> None:
        pass

    def _score(self, item: SearchItem, keywords: list[str]) -> float:
        score = 0.0
        idx = item.index_data

        if idx is None:
            self.build_index([item])
            idx = item.index_data

        for keyword in keywords:
            try:
                pattern = re.compile(keyword)
            except re.error:
                pattern = re.compile(re.escape(keyword))

            if pattern.search(idx["name"]):
                score += 3.0
            if pattern.search(idx["description"]):
                score += 2.0
            if pattern.search(idx["parameters"]):
                score += 1.0

        return score


class BM25SearchStrategy:
    """
    BM25-based search strategy.

    BM25 ranks items by term frequency, inverse document frequency,
    and document length normalization.

    Field weights:
        - Tool name ............. ×3
        - Description ........... ×2
        - Parameters ............ ×1
    """

    def __init__(self, *, k1: float = 1.5, b: float = 0.75) -> None:
        self._k1 = k1
        self._b = b
        self._avg_dl: float = 0.0
        self._idf: dict[str, float] = {}

    def build_index(self, items: list[SearchItem]) -> None:
        import math

        for item in items:
            tokens = self._tokenize(item)
            tf: dict[str, float] = {}
            for token in tokens:
                tf[token] = tf.get(token, 0.0) + 1.0
            item.index_data = {
                "tokens": tokens,
                "tf": tf,
                "dl": len(tokens),
            }

        total_dl = sum(item.index_data["dl"] for item in items)
        self._avg_dl = total_dl / len(items) if items else 0.0

        n = len(items)
        df: dict[str, int] = {}
        for item in items:
            seen: set[str] = set()
            for token in item.index_data["tokens"]:
                if token not in seen:
                    df[token] = df.get(token, 0) + 1
                    seen.add(token)

        self._idf = {}
        for term, freq in df.items():
            self._idf[term] = math.log((n - freq + 0.5) / (freq + 0.5) + 1.0)

    def search(
        self,
        query: str,
        items: list[SearchItem],
        max_results: int,
    ) -> list[SearchItem]:
        query_terms = query.lower().replace("_", " ").split()

        if not query_terms:
            return []

        scored: list[tuple[float, SearchItem]] = []
        for item in items:
            score = self._score(item, query_terms)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:max_results]]

    def cleanup(self) -> None:
        self._idf.clear()
        self._avg_dl = 0.0

    def _tokenize(self, item: SearchItem) -> list[str]:
        name_tokens = item.name.lower().replace("_", " ").split()
        desc_tokens = item.description.lower().split()
        param_tokens: list[str] = []
        for key, value in item.parameters.items():
            param_tokens.extend(key.lower().replace("_", " ").split())
            param_tokens.extend(value.lower().split())
        return name_tokens * 3 + desc_tokens * 2 + param_tokens

    def _score(self, item: SearchItem, query_terms: list[str]) -> float:
        idx = item.index_data
        assert idx is not None, "Index data must be built before scoring."

        tf = idx["tf"]
        dl = idx["dl"]
        score = 0.0

        for term in query_terms:
            if term not in self._idf:
                continue
            idf = self._idf[term]
            term_freq = tf.get(term, 0.0)
            numerator = term_freq * (self._k1 + 1.0)
            denominator = term_freq + self._k1 * (
                1.0 - self._b + self._b * dl / self._avg_dl
                if self._avg_dl > 0
                else 1.0
            )
            score += idf * numerator / denominator

        return score
