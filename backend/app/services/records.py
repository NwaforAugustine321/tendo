from app.db.tools.records import (
    create_folder, get_folders, get_folder, update_folder, delete_folder,
    create_record, get_records, get_record, update_record, delete_record,
    add_record_content, get_record_contents, delete_record_content,
)
from app.record_processor.record_agent import get_record_understanding, process_record_content
from app.record_processor.models import RecordContentInput, ProcessingStatus


async def process_content_background(business_id: str, record_id: str, content_type: str, content: str, metadata: dict):
    try:
        from app.communication.layer import sio
        await sio.emit("record_processing_status", ProcessingStatus(status="processing", record_id=record_id).model_dump())
    except Exception:
        pass

    try:
        # Process content through the knowledge pipeline (OCR for images, summarize, embed)
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

        # For images: upload to Supabase storage and use the URL
        stored_content = content
        if content_type == "image" and content and not content.startswith("http"):
            from app.db.tools.records import upload_image_to_storage
            stored_content = await upload_image_to_storage(business_id, record_id, content)

        # Save to record_content table (with storage URL for images)
        from app.db.tools.records import add_record_content
        entry = await add_record_content(business_id, record_id, content_type, stored_content)
        content_id = entry.get("id", "")

        await get_record_understanding(business_id, record_id)

        from app.events.writer import EventWriter
        EventWriter().write(
            business_id=business_id,
            entity_type="record_content",
            entity_id=content_id,
            event_type="record_content.created",
            source="system",
            payload={"record_id": record_id, "content_type": content_type, "content": stored_content},
        )

        try:
            from app.communication.layer import sio
            await sio.emit("record_processing_status", ProcessingStatus(status="completed", record_id=record_id).model_dump())
        except Exception:
            pass

    except Exception as e:
        try:
            from app.communication.layer import sio
            await sio.emit("record_processing_status", ProcessingStatus(status="failed", record_id=record_id, error=str(e)).model_dump())
        except Exception:
            pass
