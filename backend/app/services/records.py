from app.db.tools.records import (
    create_folder, get_folders, get_folder, update_folder, delete_folder,
    create_record, get_records, get_all_records, get_record, update_record, delete_record,
    add_record_content, get_record_contents, delete_record_content,
)
from app.record_knowledge.record_agent import get_record_understanding, process_record_content
from app.record_knowledge.models import RecordContentInput, ProcessingStatus


async def process_content_background(business_id: str, record_id: str, content_id: str, content_type: str, content: str, metadata: dict):
    try:
        from app.ws.socketio_server import sio
        await sio.emit("record_processing_status", ProcessingStatus(status="processing", record_id=record_id).model_dump())
    except Exception:
        pass

    try:
        record_content = RecordContentInput(
            business_id=business_id,
            record_id=record_id,
            content_type=content_type,
            content=content,
            metadata=metadata,
        )
        result = await process_record_content(record_content)
        if not result.success:
            raise Exception(result.error or "Processing failed")

        # Get the summary from the processed entry
        summary = result.entry.summary if result.entry else ""
        suggestions = result.suggested_questions or []

        from app.events.writer import EventWriter
        EventWriter().write(
            business_id=business_id,
            entity_type="record_content",
            entity_id=content_id,
            event_type="record_content.created",
            source="system",
            payload={"record_id": record_id, "content_type": content_type, "content": content},
        )

        try:
            from app.ws.socketio_server import sio
            await sio.emit("record_processing_status", ProcessingStatus(
                status="completed",
                record_id=record_id,
                summary=summary,
                suggested_questions=suggestions,
            ).model_dump())
        except Exception:
            pass

    except Exception as e:
        # Set status to failed — don't save error to content column
        try:
            from app.db.client import get_client
            client = get_client()
            client.table("record_content").update({"status": "failed"}).eq("id", content_id).execute()
        except Exception:
            pass
        try:
            from app.ws.socketio_server import sio
            await sio.emit("record_processing_status", ProcessingStatus(status="failed", record_id=record_id, error=str(e)).model_dump())
        except Exception:
            pass
