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

        path = Path(source)

        # If it's an actual file, read its contents.
        if path.is_file():
            text = path.read_text(encoding="utf-8").strip()
        else:
            # Treat source as raw text.
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
