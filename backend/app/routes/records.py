from fastapi import APIRouter, Depends, BackgroundTasks, Query

from app.lib.auth_dependency import get_current_user
from app.record_knowledge.models import CreateFolderRequest, CreateRecordRequest, UpdateRecordRequest, AddContentRequest
from app.services.records import (
    create_folder, get_folders, get_folder, update_folder, delete_folder,
    create_record, get_records, get_record, update_record, delete_record,
    add_record_content, get_record_contents, delete_record_content,
    get_record_understanding, process_content_background,
)

router = APIRouter(tags=["records"])


# --- Folder endpoints ---

@router.get("/folders")
async def list_folders(business_id: str = Query(...), user=Depends(get_current_user)):
    import logging
    logger = logging.getLogger(__name__)
    result = await get_folders(business_id)
    return result


@router.post("/folders")
async def create_folder_endpoint(body: CreateFolderRequest, user=Depends(get_current_user)):
    return await create_folder(body.business_id, body.name, body.icon, body.color)


@router.get("/folders/{folder_id}")
async def get_folder_endpoint(folder_id: str, business_id: str = Query(...), user=Depends(get_current_user)):
    return await get_folder(business_id, folder_id)


@router.put("/folders/{folder_id}")
async def update_folder_endpoint(folder_id: str, body: CreateFolderRequest, user=Depends(get_current_user)):
    return await update_folder(body.business_id, folder_id, name=body.name, icon=body.icon, color=body.color)


@router.delete("/folders/{folder_id}")
async def delete_folder_endpoint(folder_id: str, business_id: str = Query(...), user=Depends(get_current_user)):
    return await delete_folder(business_id, folder_id)


@router.get("/folders/{folder_id}/records")
async def list_records(folder_id: str, business_id: str = Query(...), user=Depends(get_current_user)):
    return await get_records(business_id, folder_id)


# --- Record endpoints ---

@router.post("/records")
async def create_record_endpoint(body: CreateRecordRequest, user=Depends(get_current_user)):
    return await create_record(body.business_id, body.folder_id, body.title)


@router.get("/records/{record_id}")
async def get_record_endpoint(record_id: str, business_id: str = Query(...), user=Depends(get_current_user)):
    return await get_record(business_id, record_id)


@router.put("/records/{record_id}")
async def update_record_endpoint(record_id: str, body: UpdateRecordRequest, user=Depends(get_current_user)):
    kwargs = {}
    if body.title:
        kwargs["title"] = body.title
    if body.folder_id:
        kwargs["folder_id"] = body.folder_id
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
    entry = await add_record_content(body.business_id, record_id, body.content_type, body.content)
    content_id = entry.get("id", "")
    background_tasks.add_task(process_content_background, body.business_id, record_id, content_id, body.content_type, body.content, body.metadata)
    return {"content": entry, "processing": True}


@router.delete("/records/{record_id}/content/{content_id}")
async def delete_content_endpoint(record_id: str, content_id: str, business_id: str = Query(...), user=Depends(get_current_user)):
    return await delete_record_content(business_id, content_id)


# --- Understanding endpoint ---

@router.get("/records/{record_id}/understanding")
async def record_understanding(record_id: str, business_id: str = Query(...), user=Depends(get_current_user)):
    result = await get_record_understanding(business_id, record_id)
    return result.model_dump()
