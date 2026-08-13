import json
import logging

from app.db.client import get_client

logger = logging.getLogger(__name__)


async def create_folder(business_id: str, name: str, icon: str = "", color: str = "") -> dict:
    client = get_client()
    data = {"business_id": business_id,
            "name": name, "icon": icon, "color": color}
    result = client.table("folders").insert(data).execute()
    return result.data[0] if result.data else data


async def get_folders(business_id: str) -> list[dict]:
    client = get_client()
    try:
        result = client.table("folders") \
            .select("*") \
            .eq("business_id", business_id) \
            .order("created_at", desc=False) \
            .execute()

        folders = result.data or []
        logger.info(
            f"get_folders business_id={business_id} returned {len(folders)} folders")

        if not folders:
            return []

        for f in folders:
            f["record_count"] = 0
            f["records"] = []

        return folders
    except Exception as e:
        logger.error(f"get_folders failed: {e}", exc_info=True)
        return []


async def get_folder(business_id: str, folder_id: str) -> dict | None:
    client = get_client()
    result = client.table("folders").select(
        "*").eq("id", folder_id).eq("business_id", business_id).single().execute()
    return result.data if result.data else None


async def update_folder(business_id: str, folder_id: str, **kwargs) -> dict:
    client = get_client()
    valid_fields = ("name", "icon", "color")
    updates = {k: v for k, v in kwargs.items(
    ) if k in valid_fields and v is not None}
    if not updates:
        return {"error": "No valid fields to update"}
    result = client.table("folders").update(updates).eq(
        "id", folder_id).eq("business_id", business_id).execute()
    return result.data[0] if result.data else {"error": "Update failed"}


async def delete_folder(business_id: str, folder_id: str) -> dict:
    client = get_client()
    try:
        client.table("folders").delete().eq("id", folder_id).eq(
            "business_id", business_id).execute()
    except Exception as e:
        logger.warning(f"Cannot delete folder {folder_id}: {e}")
        return {"error": "Cannot delete folder with existing records"}
    return {"deleted": True}


async def create_record(business_id: str, title: str, folder_id: str = "", user_id: str | None = None) -> dict:
    client = get_client()
    data = {"business_id": business_id, "title": title}
    if user_id:
        data["user_id"] = user_id
    result = client.table("records").insert(data).execute()
    return result.data[0] if result.data else data


async def get_records(business_id: str, folder_id: str = "") -> list[dict]:
    client = get_client()
    result = client.table("records").select(
        "*").eq("business_id", business_id).order("created_at", desc=False).execute()
    return result.data or []


async def get_all_records(business_id: str) -> list[dict]:
    """Fetch all records for a business with their last content as preview."""
    client = get_client()
    result = client.table("records").select("*, record_content(id, content_type, content, title, created_at)").eq(
        "business_id", business_id).order("created_at", desc=True).execute()
    records = result.data or []
    for rec in records:
        contents = rec.pop("record_content", []) or []
        contents.sort(key=lambda c: c.get("created_at", ""), reverse=True)
        last = contents[0] if contents else None
        rec["first_content"] = last["content"] if last and last.get(
            "content") else ""
        rec["content_title"] = last["title"] if last and last.get(
            "title") else ""
        rec["content_count"] = len(contents)
    return records


async def get_record(business_id: str, record_id: str) -> dict | None:
    client = get_client()
    result = client.table("records").select(
        "*").eq("id", record_id).eq("business_id", business_id).single().execute()
    return result.data if result.data else None


async def mark_record_read(business_id: str, record_id: str) -> dict:
    client = get_client()
    result = client.table("records").update({"is_read": True}).eq(
        "id", record_id).eq("business_id", business_id).execute()
    return result.data[0] if result.data else {}


async def get_unread_count(business_id: str) -> int:
    client = get_client()
    result = client.table("records").select("id", count="exact").eq(
        "business_id", business_id).eq("is_read", False).execute()
    return result.count or 0


async def get_recent_records(business_id: str, limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
    """Fetch recent records with their latest content, ordered by created_at desc.
    Supports pagination via limit/offset. Returns records and unread count."""
    client = get_client()
    result = (
        client.table("records")
        .select("*, record_content(id, content_type, content, title, created_at)", count="exact")
        .eq("business_id", business_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    records = result.data or []
    total = result.count or 0
    for rec in records:
        contents = rec.pop("record_content", []) or []
        contents.sort(key=lambda c: c.get("created_at", ""), reverse=True)
        last = contents[0] if contents else None
        rec["content"] = last["content"] if last and last.get(
            "content") else ""
        rec["content_title"] = last["title"] if last and last.get(
            "title") else ""
        rec["record_id"] = rec["id"]
    unread_count = sum(1 for rec in records if not rec.get("is_read"))
    return records, unread_count, total


async def update_record(business_id: str, record_id: str, **kwargs) -> dict:
    client = get_client()
    valid_fields = ("title",)
    updates = {k: v for k, v in kwargs.items(
    ) if k in valid_fields and v is not None}
    if not updates:
        return {"error": "No valid fields to update"}
    result = client.table("records").update(updates).eq(
        "id", record_id).eq("business_id", business_id).execute()
    return result.data[0] if result.data else {"error": "Update failed"}


async def delete_record(business_id: str, record_id: str) -> dict:
    client = get_client()
    client.table("records").delete().eq("id", record_id).eq(
        "business_id", business_id).execute()
    return {"deleted": True}


async def add_record_content(business_id: str, record_id: str, content_type: str, content: str) -> dict:
    client = get_client()
    file_url = ""

    if content.startswith("data:") and content_type != "text":
        try:
            import base64
            import uuid
            from app.config.settings import settings

            bucket_name = settings.bucket_name

            header, b64_data = content.split(",", 1)
            mime_type = header.split(":")[1].split(";")[0]  # e.g. image/png
            ext = mime_type.split("/")[1]  # e.g. png
            file_bytes = base64.b64decode(b64_data)

            file_name = f"records_files/{record_id}/{uuid.uuid4()}.{ext}"

            upload_result = client.storage.from_(bucket_name).upload(
                file_name,
                file_bytes,
                {"content-type": mime_type}
            )
            logger.info(f"Upload result: {upload_result}")

            file_url = client.storage.from_(
                bucket_name).get_public_url(file_name)
            logger.info(f"File URL: {file_url}")

            content = ""

        except Exception as e:
            logger.error(f"File upload failed: {e}", exc_info=True)

    data = {
        "business_id": business_id,
        "record_id": record_id,
        "content_type": content_type,
        "content": content,
        "file_url": file_url,
    }
    result = client.table("record_content").insert(data).execute()
    return result.data[0] if result.data else data


async def get_record_contents(business_id: str, record_id: str) -> list[dict]:
    client = get_client()
    result = client.table("record_content").select("*").eq("business_id", business_id).eq(
        "record_id", record_id).order("created_at", desc=False).execute()
    return result.data or []


async def delete_record_content(business_id: str, content_id: str) -> dict:
    client = get_client()
    client.table("record_content").delete().eq(
        "id", content_id).eq("business_id", business_id).execute()
    return {"deleted": True}


async def update_record_content(content_id: str, data: dict) -> dict:
    client = get_client()
    valid_fields = ("status", "content", "content_type", "file_url", "title")
    filtered = {k: v for k, v in data.items() if k in valid_fields}
    if not filtered:
        return {"id": content_id}
    result = client.table("record_content").update(
        filtered).eq("id", content_id).execute()
    return result.data[0] if result.data else {"id": content_id, **filtered}
