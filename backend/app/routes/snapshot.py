"""Business Snapshot REST API routes."""

import logging

from fastapi import APIRouter, HTTPException

from app.business_snapshot import generate_snapshot
from app.db.tools.snapshot import get_latest_snapshot
from app.communication.ws.server import sio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/business", tags=["business_snapshot"])


@router.get("/{business_id}/snapshot")
async def get_business_snapshot(business_id: str):
    """Return the latest business snapshot."""
    row = get_latest_snapshot(business_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail="No snapshot found for this business")
    return row
