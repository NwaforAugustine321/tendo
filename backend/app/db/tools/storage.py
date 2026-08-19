"""Storage operations — file upload for business assets."""

import base64
import logging
import uuid

from app.db.client import get_client


logger = logging.getLogger(__name__)


async def upload_file(business_id: str, path: str, content: bytes, content_type: str) -> str:
    """Upload a file to storage and return the public URL."""
    client = get_client()
    from app.config.settings import settings

    client.storage.from_(settings.bucket_name).upload(
        path=path,
        file=content,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    public_url = client.storage.from_(
        settings.bucket_name).get_public_url(path)
    logger.info(f"File uploaded: {public_url}")

    return public_url


async def upload_logo(business_id: str, content: bytes, content_type: str) -> str:
    """Upload a business logo and update the profile with the URL."""
    extension = content_type.split("/")[1]
    path = f"business_profiles/{business_id}/profiles/logo.{extension}"

    public_url = await upload_file(business_id, path, content, content_type)

    # Update the business profile logo_url
    client = get_client()
    try:
        client.table("business_profiles").update(
            {"logo_url": public_url}).eq("id", business_id).execute()
        logger.info(f"Logo URL saved to profile: {business_id}")
    except Exception as e:
        logger.warning(f"Failed to update profile logo_url: {e}")

    return public_url


async def upload_business_logo(business_id: str, logo_data_url: str, **kwargs) -> dict:
    """Upload a business logo from a base64 data URL.

    Used by agents that receive logo as data URL from the frontend.
    """
    try:
        if not logo_data_url.startswith("data:"):
            return {"error": "Invalid data URL format"}

        header, encoded = logo_data_url.split(",", 1)
        mime_type = header.split(":")[1].split(";")[0]
        file_bytes = base64.b64decode(encoded)

        public_url = await upload_logo(business_id, file_bytes, mime_type)
        return {"logo_url": public_url, "success": True}

    except Exception as e:
        logger.error(f"Logo upload failed: {e}")
        return {"error": str(e), "success": False}
