"""Upload routes — file uploads to Storage."""

import logging

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query

from app.config.settings import settings
from app.db.client import get_client
from app.lib.auth_dependency import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    business_id: str = Query(default="default"),
    user: dict = Depends(get_current_user),
):
    """Upload a business logo to Storage and return the public URL."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File must be 20MB or less")

    extension = file.content_type.split("/")[1]
    file_name = f"business_profiles/{business_id}/profiles/logo.{extension}"

    try:
        client = get_client()
        client.storage.from_(settings.bucket_name).upload(
            path=file_name,
            file=content,
            file_options={"content-type": file.content_type, "upsert": "true"},
        )
        public_url = client.storage.from_(settings.bucket_name).get_public_url(file_name)
        logger.info(f"Logo uploaded: {public_url}")

        if business_id and business_id != "default":
            try:
                client.table("business_profiles").update({"logo_url": public_url}).eq("id", business_id).execute()
                logger.info(f"Logo URL saved to profile: {business_id}")
            except Exception as e:
                logger.warning(f"Failed to update profile logo_url: {e}")

        return {"url": public_url}
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")
