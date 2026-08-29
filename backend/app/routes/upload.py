"""Upload routes — thin HTTP layer."""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query

from app.lib.auth_dependency import get_current_user
from app.services.upload import upload_business_logo

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/logo")
async def upload_logo_route(
    file: UploadFile = File(...),
    business_id: str = Query(default="default"),
    user: dict = Depends(get_current_user),
):
    """Upload a business logo and return the public URL."""
    content = await file.read()
    try:
        url = await upload_business_logo(business_id, content, file.content_type or "")
        return {"url": url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Upload failed")
