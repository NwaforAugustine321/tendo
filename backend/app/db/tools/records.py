import json
import logging

from langchain_core.tools import tool

from app.db.client import get_client
from app.memory.memory import Memory

logger = logging.getLogger(__name__)


async def create_folder(business_id: str, name: str, icon: str = "", color: str = "") -> dict:
    client = get_client()
    data = {"business_id": business_id, "name": name, "icon": icon, "color": color}
    result = client.table("folders").insert(data).execute()
    return result.data[0] if result.data else data


async def get_folders(business_id: str) -> list[dict]:
    client = get_client()
    try:
        result = client.table("folders").select("*").eq("business_id", business_id).order("created_at", desc=False).execute()
        folders = result.data or []
        logger.info(f"get_folders business_id={business_id} returned {len(folders)} folders")

        for f in folders:
            try:
                records_result = client.table("records").select("id, title, created_at, updated_at").eq("folder_id", f["id"]).order("created_at", desc=False).execute()
                f["records"] = records_result.data or []
                f["record_count"] = len(f["records"])
            except Exception:
                f["records"] = []
                f["record_count"] = 0

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


async def create_record(business_id: str, folder_id: str, title: str) -> dict:
    client = get_client()
    data = {"business_id": business_id, "folder_id": folder_id, "title": title}
    result = client.table("records").insert(data).execute()
    return result.data[0] if result.data else data


async def get_records(business_id: str, folder_id: str) -> list[dict]:
    client = get_client()
    result = client.table("records").select("*").eq("business_id", business_id).eq("folder_id", folder_id).order("created_at", desc=False).execute()
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


def get_record_knowledge_tools(business_id: str, record_id: str) -> list:
    from app.record_knowledge.store import _get_storage

    @tool
    async def search_record_knowledge(query: str = "", limit: int = 10) -> str:
        """Search knowledge stored for this record by semantic similarity."""
        try:
            memory = Memory(scope=f"/{business_id}/{record_id}", storage=_get_storage())
            results = await memory.recall(query=query, limit=limit)
            entries = [{"summary": m.record.content, "type": (m.record.metadata or {}).get("content_type", "")} for m in results]
            return json.dumps(entries, default=str)
        except Exception as e:
            logger.warning(f"search_record_knowledge failed: {e}")
            return json.dumps([])

    @tool
    async def search_business_knowledge(query: str = "", limit: int = 10) -> str:
        """Search business-level knowledge. Always use this first to understand business context pf what already happened in the business"""
        try:
            memory = Memory(scope=f"/insights/{business_id}")
            results = await memory.recall(query=query, limit=limit)
            entries = [{"summary": m.record.content} for m in results]
            return json.dumps(entries, default=str)
        except Exception as e:
            logger.warning(f"search_business_knowledge failed: {e}")
            return json.dumps([])

    return [search_record_knowledge, search_business_knowledge]
