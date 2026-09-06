
from __future__ import annotations

import logging

from app.background.factory import create_task

from ..contracts import WebhookEvent


logger = logging.getLogger(__name__)


class DocumentIngestionWebhookHandler:

    def __init__(
        self,
    ) -> None:
        pass

    async def handle(
        self,
        event: WebhookEvent,
    ) -> None:
        payload = event.payload

        document_id = payload.get(
            "document_id",
        )

        business_id = payload.get(
            "business_id",
        )

        collection_type = payload.get(
            "collection_type",
        )

        if not isinstance(
            document_id,
            str,
        ) or not document_id.strip():
            logger.error(
                "[DOCUMENT WEBHOOK] Missing document_id "
                "event_id=%s request_id=%s",
                event.event_id,
                event.request_id,
            )
            return

        if not isinstance(
            business_id,
            str,
        ) or not business_id.strip():
            logger.error(
                "[DOCUMENT WEBHOOK] Missing business_id "
                "document_id=%s",
                document_id,
            )
            return

        if not isinstance(
            collection_type,
            str,
        ) or not collection_type.strip():
            logger.error(
                "[DOCUMENT WEBHOOK] Missing collection_type "
                "document_id=%s",
                document_id,
            )
            return

        await create_task(
            job_type="document_processing",
            payload={
                "document_id": document_id.strip(),
                "business_id": business_id.strip(),
                "collection_type": collection_type.strip(),
            },
        )

        logger.info(
            "[DOCUMENT WEBHOOK] Document processing job created "
            "document_id=%s business_id=%s collection_type=%s "
            "event_id=%s request_id=%s",
            document_id,
            business_id,
            collection_type,
            event.event_id,
            event.request_id,
        )
