"""Upload service — validates and orchestrates file uploads."""

import logging

from app.db.tools.storage import upload_logo

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


async def upload_business_logo(business_id: str, content: bytes, content_type: str) -> str:
    """Validate and upload a business logo. Returns the public URL."""
    if not content_type or not content_type.startswith("image/"):
        raise ValueError("File must be an image")

    if len(content) > MAX_FILE_SIZE:
        raise ValueError("File must be 20MB or less")

    return await upload_logo(business_id, content, content_type)
