from __future__ import annotations

from pathlib import Path
from typing import Any

from app.runtime.rag.models import (
    RAGDocument,
)

from ..loader import (
    DocumentLoader,
)


class MarkdownLoader(
    DocumentLoader,
):
    """
    Loads Markdown into one RAG document.

    Markdown is preserved exactly as provided.
    Splitting is handled by the DocumentSplitter.
    """

    async def load(
        self,
        *,
        source: str | Path | Any,
    ) -> list[RAGDocument]:

        markdown = str(source).strip()

        if not markdown:
            return []

        return [
            RAGDocument(
                id="",
                title="",
                source="markdown",
                content=markdown,
                metadata={},
            )
        ]
