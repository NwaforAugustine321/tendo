"""Supabase Storage operations — file upload for business assets."""

import base64
import logging
import uuid

from app.db.client import get_client
from app.db.registry import register

logger = logging.getLogger(__name__)


@register("upload_business_logo")
async def upload_business_logo(business_id: str, logo_data_url: str, **kwargs) -> dict:
    """Upload a business logo to Supabase Storage and update the profile.

    Args:
        business_id: The business ID.
        logo_data_url: Base64 data URL (e.g., data:image/png;base64,...)

    Returns:
        Dict with the public URL of the uploaded logo.
    """
    client = get_client()

    try:
        from app.config.settings import settings
        bucket_name = settings.bucket_name
        # Parse the data URL
        if not logo_data_url.startswith("data:"):
            return {"error": "Invalid data URL format"}

        header, encoded = logo_data_url.split(",", 1)
        mime_type = header.split(":")[1].split(";")[0]
        extension = mime_type.split("/")[1]  # png, jpeg, webp, etc.

        # Decode the base64 data
        file_bytes = base64.b64decode(encoded)

        # Generate unique file path
        file_name = f"business_profiles/{business_id}/logo_{uuid.uuid4().hex[:8]}.{extension}"

        # Upload to Supabase Storage
        client.storage.from_(bucket_name).upload(
            path=file_name,
            file=file_bytes,
            file_options={"content-type": mime_type, "upsert": "true"},
        )

        # Get public URL
        public_url = client.storage.from_(bucket_name).get_public_url(file_name)

        # Update business profile with the logo URL
        client.table("business_profiles").update(
            {"logo_url": public_url}
        ).eq("id", business_id).execute()

        logger.info(f"Logo uploaded for business {business_id}: {public_url}")
        return {"logo_url": public_url, "success": True}

    except Exception as e:
        logger.error(f"Logo upload failed: {e}")
        return {"error": str(e), "success": False}
