from __future__ import annotations

import logging
from uuid import uuid4

from ..ingestion.default_loader import (
    DefaultDocumentLoader,
)
from ..ingestion.pipeline import (
    DocumentIngestionPipeline,
)
from ..ingestion.default_splitter import (
    DefaultDocumentSplitter,
)
from ..lancedb import LanceRAGStore

from .interface import ContentProcessor
from .models import (
    ProcessingMetadata,
    ProcessingResult,
    RecordContentInput,
)
from ...agent_hub.content_summarizer.summarizer import content_summarizer
from ...event_writer.default_event_writer import EventWriter

logger = logging.getLogger(__name__)


class DocumentProcessor(
    ContentProcessor,
):
    """
    Processes document content through the existing
    document ingestion pipeline.

    Flow:

        Source
          ↓
        Loader
          ↓
        Documents
          ↓
        Splitter
          ↓
        Chunks
          ↓
        RAG Store
          ↓
        Event metadata attached to chunks
          ↓
        ProcessingResult
    """

    def __init__(
        self,
        *,
        store: LanceRAGStore,
        event_writer: EventWriter,
    ) -> None:

        self._store = store
        self._event_writer = event_writer

        self._pipeline = DocumentIngestionPipeline(
            loader=DefaultDocumentLoader(),
            splitter=DefaultDocumentSplitter(),
            store=self._store,
        )

    async def process(
        self,
        business_id: str,
        record_content: RecordContentInput,
    ) -> ProcessingResult:

        try:

            content = (
                record_content.content
                or ""
            ).strip()

            if not content:
                return ProcessingResult(
                    success=False,
                    error="No content to process.",
                )

            result = await self._pipeline.ingest(
                source=content,
                content_type=record_content.content_type,
            )

            if result.chunks == 0:
                return ProcessingResult(
                    success=False,
                    documents=result.documents,
                    chunks=0,
                    entries=[],
                    error="No chunks produced from content.",
                )

            document_key = str(
                uuid4(),
            )

            total_chunks = len(
                result.entries,
            )

            for chunk_index, chunk in enumerate(
                result.entries,
                start=1,
            ):

                chunk.metadata.update(
                    {
                        "document_key": document_key,
                        "chunk_index": chunk_index,
                        "total_chunks": total_chunks,
                    }
                )

                await self._event_writer.write_chunk(
                    business_id=business_id,
                    event_type="document_chunk",
                    document_key=document_key,
                    chunk_index=chunk_index,
                    total_chunks=total_chunks,
                    payload=chunk.content,
                )

            title = ""

            rolling_summary = ""

            suggested_questions: list[str] = []

            max_metadata_chunks = 20

            for chunk in result.entries[
                :max_metadata_chunks
            ]:

                if rolling_summary:

                    text_to_summarize = (
                        "[Previous Summary]\n"
                        f"{rolling_summary}\n\n"
                        "[New Content]\n"
                        f"{chunk.content}"
                    )

                else:

                    text_to_summarize = (
                        chunk.content
                    )

                summary_result = (
                    await content_summarizer(
                        text_to_summarize,
                    )
                )

                title = (
                    summary_result.get(
                        "title",
                        "",
                    )
                    or title
                )

                rolling_summary = (
                    summary_result.get(
                        "summary",
                        "",
                    )
                )

                suggested_questions = (
                    summary_result.get(
                        "suggested_questions",
                        [],
                    )
                    or suggested_questions
                )

            logger.info(
                "Document processing complete: "
                "documents=%s chunks=%s "
                "document_key=%s",
                result.documents,
                total_chunks,
                document_key,
            )

            return ProcessingResult(
                success=True,
                documents=result.documents,
                chunks=total_chunks,
                entries=result.entries,
                metadata=ProcessingMetadata(
                    title=title,
                    summary=rolling_summary,
                    suggested_questions=(
                        suggested_questions
                    ),
                ),
            )

        except Exception as exc:

            logger.exception(
                "Failed to process document content.",
            )

            return ProcessingResult(
                success=False,
                error=str(exc),
            )
