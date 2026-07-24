import json
import logging

from app.db.client import get_client

logger = logging.getLogger(__name__)


async def create_folder(business_id: str, name: str, icon: str = "", color: str = "") -> dict:
    client = get_client()
    data = {"business_id": business_id, "name": name, "icon": icon, "color": color}
    result = client.table("folders").insert(data).execute()
    return result.data[0] if result.data else data


async def get_folders(business_id: str) -> list[dict]:
    client = get_client()
    try:
        result = client.table("folders") \
            .select("*, records(id, title, folder_id, created_at, updated_at)") \
            .eq("business_id", business_id) \
            .eq("records.business_id", business_id) \
            .order("created_at", desc=False) \
            .order("created_at", foreign_table="records", desc=False) \
            .execute()
            
        folders = result.data or []
        logger.info(f"get_folders business_id={business_id} returned {len(folders)} folders")

        if not folders:
            return []

        for f in folders:
            folder_records = f.get("records") or []
            f["record_count"] = len(folder_records)

        return folders
    except Exception as e:
        logger.error(f"get_folders failed: {e}", exc_info=True)
        return []


async def get_folder(business_id: str, folder_id: str) -> dict | None:
    client = get_client()
    result = client.table("folders").select("*").eq("id", folder_id).eq("business_id", business_id).single().execute()
    return result.data if result.data else None


async def update_folder(business_id: str, folder_id: str, **kwargs) -> dict:
    client = get_client()
    valid_fields = ("name", "icon", "color")
    updates = {k: v for k, v in kwargs.items() if k in valid_fields and v is not None}
    if not updates:
        return {"error": "No valid fields to update"}
    result = client.table("folders").update(updates).eq("id", folder_id).eq("business_id", business_id).execute()
    return result.data[0] if result.data else {"error": "Update failed"}


async def delete_folder(business_id: str, folder_id: str) -> dict:
    client = get_client()
    try:
        client.table("folders").delete().eq("id", folder_id).eq("business_id", business_id).execute()
    except Exception as e:
        logger.warning(f"Cannot delete folder {folder_id}: {e}")
        return {"error": "Cannot delete folder with existing records"}
    return {"deleted": True}


async def create_record(business_id: str, folder_id: str, title: str, user_id: str | None = None) -> dict:
    client = get_client()
    data = {"business_id": business_id, "title": title}
    if folder_id:
        data["folder_id"] = folder_id
    if user_id:
        data["user_id"] = user_id
    result = client.table("records").insert(data).execute()
    return result.data[0] if result.data else data


async def get_records(business_id: str, folder_id: str) -> list[dict]:
    client = get_client()
    result = client.table("records").select("*").eq("business_id", business_id).eq("folder_id", folder_id).order("created_at", desc=False).execute()
    return result.data or []


async def get_all_records(business_id: str) -> list[dict]:
    """Fetch all records for a business regardless of folder."""
    client = get_client()
    result = client.table("records").select("*").eq("business_id", business_id).order("created_at", desc=True).execute()
    return result.data or []


async def get_record(business_id: str, record_id: str) -> dict | None:
    client = get_client()
    result = client.table("records").select("*").eq("id", record_id).eq("business_id", business_id).single().execute()
    return result.data if result.data else None


async def update_record(business_id: str, record_id: str, **kwargs) -> dict:
    client = get_client()
    valid_fields = ("title", "folder_id")
    updates = {k: v for k, v in kwargs.items() if k in valid_fields and v is not None}
    if not updates:
        return {"error": "No valid fields to update"}
    result = client.table("records").update(updates).eq("id", record_id).eq("business_id", business_id).execute()
    return result.data[0] if result.data else {"error": "Update failed"}


async def delete_record(business_id: str, record_id: str) -> dict:
    client = get_client()
    client.table("records").delete().eq("id", record_id).eq("business_id", business_id).execute()
    return {"deleted": True}


async def add_record_content(business_id: str, record_id: str, content_type: str, content: str) -> dict:
    client = get_client()
    data = {"business_id": business_id, "record_id": record_id, "content_type": content_type, "content": content}
    result = client.table("record_content").insert(data).execute()
    return result.data[0] if result.data else data


async def get_record_contents(business_id: str, record_id: str) -> list[dict]:
    client = get_client()
    result = client.table("record_content").select("*").eq("business_id", business_id).eq("record_id", record_id).order("created_at", desc=False).execute()
    return result.data or []


async def delete_record_content(business_id: str, content_id: str) -> dict:
    client = get_client()
    client.table("record_content").delete().eq("id", content_id).eq("business_id", business_id).execute()
    return {"deleted": True}

