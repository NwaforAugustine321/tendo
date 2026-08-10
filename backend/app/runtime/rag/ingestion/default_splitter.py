from __future__ import annotations

from copy import deepcopy

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
)

from app.runtime.rag.models import (
    RAGDocument,
)

from .splitter import (
    DocumentSplitter,
)


class DefaultDocumentSplitter(
    DocumentSplitter,
):
    """
    Default recursive character splitter.
    """

    def __init__(
        self,
        *,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:

        self._splitter = (
            RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=[
                    "\n\n",
                    "\n",
                    ". ",
                    " ",
                    "",
                ],
            )
        )

    async def split(
        self,
        documents: list[RAGDocument],
    ) -> list[RAGDocument]:

        chunks: list[RAGDocument] = []

        for document in documents:

            parts = self._splitter.split_text(
                document.content,
            )

            if not parts:
                continue

            for index, part in enumerate(parts):

                metadata = deepcopy(
                    document.metadata,
                )

                metadata["chunk"] = index

                chunks.append(
                    RAGDocument(
                        id=document.id,
                        title=document.title,
                        source=document.source,
                        content=part,
                        score=document.score,
                        metadata=metadata,
                    )
                )

        return chunks
