from fastapi import APIRouter, Depends, BackgroundTasks, Query

from app.lib.auth_dependency import get_current_user
from app.record_knowledge.models import CreateFolderRequest, CreateRecordRequest, UpdateRecordRequest, AddContentRequest
from app.services.records import (
    create_folder, get_folders, get_folder, update_folder, delete_folder,
    create_record, get_records, get_all_records, get_record, update_record, delete_record,
    add_record_content, get_record_contents, delete_record_content
)
from app.db.tools.records import mark_record_read, get_unread_count, get_recent_records
from app.runtime.agent_hub.content_insight_generator.generator import content_insight_generator
from ..background.factory import create_task
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["records"])


@router.get("/records")
async def list_all_records(business_id: str = Query(...), user=Depends(get_current_user)):
    return await get_all_records(business_id)


@router.get("/records/recent")
async def recent_records_endpoint(business_id: str = Query(...), limit: int = Query(20), offset: int = Query(0), user=Depends(get_current_user)):
    records, unread_count, total = await get_recent_records(business_id, limit=limit, offset=offset)
    return {"records": records, "count": unread_count, "total": total}


@router.post("/records")
async def create_record_endpoint(body: CreateRecordRequest, user=Depends(get_current_user)):
    return await create_record(body.business_id, body.title)


@router.get("/records/{record_id}")
async def get_record_endpoint(record_id: str, business_id: str = Query(...), user=Depends(get_current_user)):
    return await get_record(business_id, record_id)


@router.put("/records/{record_id}")
async def update_record_endpoint(record_id: str, body: UpdateRecordRequest, user=Depends(get_current_user)):
    kwargs = {}
    if body.title:
        kwargs["title"] = body.title
    return await update_record(body.business_id, record_id, **kwargs)


@router.delete("/records/{record_id}")
async def delete_record_endpoint(record_id: str, business_id: str = Query(...), user=Depends(get_current_user)):
    return await delete_record(business_id, record_id)


# --- Record content endpoints ---

@router.get("/records/{record_id}/content")
async def list_record_content(record_id: str, business_id: str = Query(...), user=Depends(get_current_user)):
    return await get_record_contents(business_id, record_id)


@router.post("/records/{record_id}/content")
async def add_content_endpoint(record_id: str, body: AddContentRequest, background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    if body.content.startswith("data:") and "/" in body.content.split(",")[0]:
        mime = body.content.split(",")[0].split(":")[1].split(";")[0]
        processing_content_type = mime.split("/")[-1]

    await create_task(
        job_type='document_processing',
        payload={
            "business_id": body.business_id,
            "content_type": processing_content_type,
            "user_id": user["user_id"],
            "content": body.content,
            "record_id": record_id
        }
    )

    return {"content": {}, "processing": True}


@router.delete("/records/{record_id}/content/{content_id}")
async def delete_content_endpoint(record_id: str, content_id: str, business_id: str = Query(...), user=Depends(get_current_user)):
    return await delete_record_content(business_id, content_id)


# --- Understanding endpoint ---

@router.get("/records/{record_id}/understanding")
async def record_understanding(record_id: str, business_id: str = Query(...), user=Depends(get_current_user)):
    try:
        # return await content_insight_generator(business_id, record_id)
        return {"insight": "", "suggestions": []}
    except Exception as e:
        logger.error(f"Understanding generation failed: {e}", exc_info=True)
        return {"insight": "", "suggestions": []}


# --- Mark-as-read ---

@router.post("/records/{record_id}/read")
async def mark_read_endpoint(record_id: str, business_id: str = Query(...), user=Depends(get_current_user)):
    await mark_record_read(business_id, record_id)
    return {"status": "read"}
