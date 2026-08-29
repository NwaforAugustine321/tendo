from __future__ import annotations

import logging
from typing import Any

from ..worker import BackgroundWorker
from uuid import uuid4

from app.db.tools.records import (
    add_record_content, create_record,
    update_record_content, get_record
)
from app.communication.events import ApplicationEvent
from ...runtime.rag.lancedb import LanceRAGStore
from ...runtime.rag.document.processor import DocumentProcessor
from ...runtime.rag.document.models import RecordContentInput
from ...runtime.event_writer.default_event_writer import EventWriter
from ...db.client import get_client
from ...communication.event_bus import get_event_bus
from ...communication.events import EventDelivery

logger = logging.getLogger(__name__)


class BusinessDocumentProcessorBWorker(
    BackgroundWorker,
):
    """
    Background worker for document/event processing.
    """

    def __init__(
        self,
    ) -> None:

        super().__init__(
            job_type="document_processing",
            worker_name="document-processing",
        )

        self._db = get_client()
        self._event_writer: EventWriter = EventWriter(db=self._db)

    async def process(
        self,
        job: dict[str, Any],
    ) -> dict[str, Any] | None:
        content_id = ''

        try:

            payload = self.get_payload(
                job,
            )

            user_id = payload.get(
                "user_id",
            )

            if not user_id:
                raise ValueError(
                    "'user_id' cannot be empty.",
                )

            processing_payload = {
                "type": "document.progress",
                "user_id": user_id,
                "event": "document.progress",
            }

            processing_payload.update({
                "status": "Processing",
                "message": 'Document is Processing'
            })
            await get_event_bus().publish(
                ApplicationEvent(
                    event="document.progress",
                    source="document_processor",
                    delivery=EventDelivery.APP,
                    data=processing_payload,
                ),
            )

            job_id = self.get_id(
                job,
            )

            if job_id is None:
                raise ValueError(
                    "Document processing job requires 'id'.",
                )

            job_id = job_id.strip()

            if not job_id:
                processing_payload.update({
                    "status": "Failed",
                    "message": 'Document Processing Failed'
                })
                await get_event_bus().publish(
                    ApplicationEvent(
                        event="document.progress",
                        source="document_processor",
                        delivery=EventDelivery.APP,
                        data=processing_payload,
                    ),
                )
                raise ValueError(
                    "Document processing job 'id' "
                    "cannot be empty.",
                )

            business_id = payload.get(
                "business_id",
            )

            content_type = payload.get(
                "content_type",
            )

            content = payload.get(
                "content",
            )

            record_id = payload.get(
                "record_id",
            )

            if not business_id:
                processing_payload.update({
                    "status": "Failed",
                    "message": 'Document Processing Failed'
                })
                await get_event_bus().publish(
                    ApplicationEvent(
                        event="document.progress",
                        source="document_processor",
                        delivery=EventDelivery.APP,
                        data=processing_payload,
                    ),
                )

                raise ValueError(
                    "'business_id' cannot be empty.",
                )

            if not content:
                processing_payload.update({
                    "status": "Failed",
                    "message": 'Document Processing Failed'
                })
                await get_event_bus().publish(
                    ApplicationEvent(
                        event="document.progress",
                        source="document_processor",
                        delivery=EventDelivery.APP,
                        data=processing_payload,
                    ),
                )
                raise ValueError(
                    "'content' cannot be empty.",
                )

            if not content_type:
                processing_payload.update({
                    "status": "Failed",
                    "message": 'Document Processing Failed'
                })
                await get_event_bus().publish(
                    ApplicationEvent(
                        event="document.progress",
                        source="document_processor",
                        delivery=EventDelivery.APP,
                        data=processing_payload,
                    ),
                )
                raise ValueError(
                    "'content type' cannot be empty.",
                )

            hash_id = uuid4().hex[:6]
            title = f"#{hash_id}"

            if record_id:
                record = await get_record(business_id, record_id)
            else:
                record = await create_record(
                    business_id, title
                )

            record_id = record.get("id", "")

            entry = await add_record_content(business_id, record_id, content_type, content)
            content_id = entry.get("id", "")

            scopes = [f"business/{business_id}",
                      f"business/{business_id}/record/{record_id}"]

            store = LanceRAGStore(namespace=business_id, scopes=scopes)
            processor = DocumentProcessor(
                store=store, event_writer=self._event_writer)

            record_content = RecordContentInput(
                content=content,
                content_type=content_type,
            )

            result = await processor.process(
                business_id=business_id,
                record_content=record_content,
            )

            title = result.metadata.title
            summary = result.metadata.summary
            suggested_questions = result.metadata.suggested_questions

            await update_record_content(content_id, {"status": "completed", "content": summary, "title": title})

            processing_payload.update({
                "status": "Completed",
                "message": 'Document Processing Completed',
                "data": {
                    "title": title,
                    "summary": summary,
                    "suggested_questions": suggested_questions
                }
            })
            await get_event_bus().publish(
                ApplicationEvent(
                    event="document.progress",
                    source="document_processor",
                    delivery=EventDelivery.APP,
                    data=processing_payload,
                ),
            )

            if hasattr(
                result,
                "model_dump",
            ):
                return result.model_dump()

            return {
                "success": result.success,
                "documents": result.documents,
                "chunks": result.chunks,
            }

        except Exception as error:
            try:
                await update_record_content(content_id, {"status": "failed"})
            except e as err:
                raise err
            raise error
