from app.db.client import get_client


def get_whatsapp_data_sources() -> list[dict]:
    """Get all WhatsApp data sources with business_id and data."""
    client = get_client()
    result = client.table("data_sources").select("business_id, data").eq("source_type", "whatsapp").execute()
    return result.data or []


def get_business_id_by_phone_number(phone_number_id: str) -> str | None:
    """Resolve business_id from a WhatsApp phone_number_id."""
    rows = get_whatsapp_data_sources()
    for row in rows:
        data = row.get("data") or {}
        if str(data.get("phone_number_id")) == str(phone_number_id):
            return row["business_id"]
    return None


def update_record_content_status(content_id: str, business_id: str, status: str, content: str | None = None):
    """Update record_content row status and optionally content."""
    client = get_client()
    update_data = {"status": status}
    if content is not None:
        update_data["content"] = content
    client.table("record_content").update(update_data).eq("id", content_id).eq("business_id", business_id).execute()
