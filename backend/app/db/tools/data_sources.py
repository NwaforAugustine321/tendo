from app.db.client import get_client


def get_whatsapp_data_sources() -> list[dict]:
    """Get all WhatsApp data sources with business_id and data."""
    client = get_client()
    result = client.table("data_sources").select(
        "business_id, data").eq("source_type", "whatsapp").execute()
    return result.data or []


def get_business_id_by_phone_number(phone_number_id: str) -> str | None:
    """Resolve business_id from a WhatsApp phone_number_id."""
    import json as _json
    rows = get_whatsapp_data_sources()
    for row in rows:
        data = row.get("data") or {}
        # Handle case where data is a JSON string instead of a dict
        if isinstance(data, str):
            try:
                data = _json.loads(data)
            except (ValueError, TypeError):
                continue
        if str(data.get("phone_number_id", "")) == str(phone_number_id):
            return row["business_id"]
    return None


def get_business_owner_by_phone_number(
    phone_number_id: str,
) -> tuple[str, str] | None:
    """
    Resolve (business_id, user_id) from a WhatsApp phone_number_id.

    'data_sources' does not store the user, so the owning user is
    resolved from 'business_profiles.user_id'.

    Returns None when the phone number maps to no business, or when
    the business has no owning user.
    """

    business_id = get_business_id_by_phone_number(
        phone_number_id,
    )

    if not business_id:
        return None

    client = get_client()

    result = (
        client.table("business_profiles")
        .select("user_id")
        .eq("id", business_id)
        .maybe_single()
        .execute()
    )

    if not result or not result.data:
        return None

    user_id = result.data.get("user_id")

    if not user_id:
        return None

    return business_id, str(user_id)


def update_record_content_status(content_id: str, business_id: str, status: str, content: str | None = None):
    """Update record_content row status and optionally content."""
    client = get_client()
    update_data = {"status": status}
    if content is not None:
        update_data["content"] = content
    client.table("record_content").update(update_data).eq(
        "id", content_id).eq("business_id", business_id).execute()
