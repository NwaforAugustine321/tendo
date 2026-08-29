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


def get_whatsapp_business_owner(
    phone_number_id: str,
) -> tuple[str, str | None] | None:
    """
    Resolve (business_id, user_id) for a WhatsApp phone_number_id
    in a single request.

    'business_profiles' is embedded through the
    data_sources.business_id foreign key, so the owning user comes
    back in the same round trip.

    Returns:
        None                    -> no data source matches the number
        (business_id, None)     -> matched, but business has no user
        (business_id, user_id)  -> resolved
    """

    import json as _json

    if not phone_number_id:
        return None

    client = get_client()

    try:
        result = (
            client.table("data_sources")
            .select("business_id, data, business_profiles(user_id)")
            .eq("source_type", "whatsapp")
            .execute()
        )
    except Exception:
        return None

    rows = (result.data or []) if result else []

    for row in rows:
        data = row.get("data") or {}

        # 'data' is JSONB, but existing rows may hold a
        # JSON-encoded string rather than an object.
        if isinstance(data, str):
            try:
                data = _json.loads(data)
            except (ValueError, TypeError):
                continue

        if str(data.get("phone_number_id", "")) != str(phone_number_id):
            continue

        business_id = row.get("business_id")

        if not business_id:
            return None

        # Embedded relation arrives as a dict (many-to-one) or a
        # single-element list depending on client version.
        profile = row.get("business_profiles")

        if isinstance(profile, list):
            profile = profile[0] if profile else None

        user_id = (
            profile.get("user_id")
            if isinstance(profile, dict)
            else None
        )

        return (
            str(business_id),
            str(user_id) if user_id else None,
        )

    return None


def get_business_user_id(business_id: str) -> str | None:
    """
    Resolve the owning user_id for a business.

    'data_sources' does not store the user, so it is read from
    'business_profiles.user_id'.

    Returns None when the business row is missing or has no user.
    """

    if not business_id:
        return None

    client = get_client()

    try:
        result = (
            client.table("business_profiles")
            .select("user_id")
            .eq("id", business_id)
            .limit(1)
            .execute()
        )
    except Exception:
        return None

    rows = (result.data or []) if result else []

    if not rows:
        return None

    user_id = rows[0].get("user_id")

    return str(user_id) if user_id else None


def update_record_content_status(content_id: str, business_id: str, status: str, content: str | None = None):
    """Update record_content row status and optionally content."""
    client = get_client()
    update_data = {"status": status}
    if content is not None:
        update_data["content"] = content
    client.table("record_content").update(update_data).eq(
        "id", content_id).eq("business_id", business_id).execute()
