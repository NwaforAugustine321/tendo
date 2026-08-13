import logging

from app.db.tools.records import (
    create_folder, get_folders, get_folder, update_folder, delete_folder,
    create_record, get_records, get_all_records, get_record, update_record, delete_record,
    add_record_content, get_record_contents, delete_record_content,
    update_record_content,
)
from app.record_knowledge.record_agent import process_record_content
from app.record_knowledge.models import RecordContentInput, ProcessingStatus
from app.ws.socketio_server import sio

logger = logging.getLogger(__name__)


async def process_content_background(business_id: str, record_id: str, content_id: str, content_type: str, content: str, metadata: dict, file_url: str = ""):

    try:
        record_content = RecordContentInput(
            business_id=business_id,
            record_id=record_id,
            content_type=content_type,
            content=content,
            file_url=file_url,
            metadata=metadata,
        )

        result = await process_record_content(record_content)
        if not result.success:
            raise Exception(result.error or "Processing failed")

        title = result.title
        summary = result.summary

        await update_record_content(content_id, {"status": "completed", "content": summary, "title": title})

        try:
            await sio.emit("record_processing_status", ProcessingStatus(
                status="completed",
                record_id=record_id,
                summary=summary,
                suggested_questions=result.suggested_questions,
            ).model_dump())
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Content processing failed: {e}", exc_info=True)
        try:
            await update_record_content(content_id, {"status": "failed"})
        except Exception:
            pass
