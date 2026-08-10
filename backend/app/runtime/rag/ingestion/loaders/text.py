from __future__ import annotations

from pathlib import Path
from typing import Any

from app.runtime.rag.models import (
    RAGDocument,
)

from ..loader import (
    DocumentLoader,
)


class TextLoader(
    DocumentLoader,
):
    """
    Loads plain text into one RAG document.
    """

    async def load(
        self,
        *,
        source: str | Path | Any,
    ) -> list[RAGDocument]:

        text = str(source).strip()

        if not text:
            return []

        return [
            RAGDocument(
                id="",
                title="",
                source="text",
                content=text,
                metadata={},
            )
        ]
