

from app.services.integrations import (
    handle_whatsapp_verification,
    handle_whatsapp_webhook,
    list_data_sources as svc_list_data_sources,
    connect_data_source as svc_connect_data_source,
    disconnect_data_source as svc_disconnect_data_source,
    onboard_whatsapp_business,
)
from app.lib.auth_dependency import get_current_user
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["integrations"])


class ConnectCallbackRequest(BaseModel):
    business_id: str
    source_type: str
    details: dict = {}


class WhatsAppOnboardRequest(BaseModel):
    business_id: str
    code: str
    waba_id: str | None = None
    phone_number_id: str | None = None


@router.get("/webhook/whatsapp")
async def whatsapp_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    status_code, body = handle_whatsapp_verification(
        hub_mode, hub_challenge, hub_verify_token)
    return PlainTextResponse(content=body, status_code=status_code)


@router.post("/webhook/whatsapp")
async def whatsapp_receive(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    try:
        payload = await request.json()
    except Exception:
        payload = {}
    print(payload)
    status_code, _ = await handle_whatsapp_webhook(raw_body, signature, payload, background_tasks)
    return Response(status_code=status_code)


@router.post("/whatsapp/onboard")
async def whatsapp_onboard(
    body: WhatsAppOnboardRequest,
    user: dict = Depends(get_current_user),
):
    try:
        result = await onboard_whatsapp_business(
            business_id=body.business_id,
            code=body.code,
            waba_id=body.waba_id,
            phone_number_id=body.phone_number_id,
        )
        return result
    except Exception as e:
        logger.error("WhatsApp onboard error: %s", e)
        return Response(status_code=400)


@router.get("/data-sources")
async def list_sources(
    business_id: str = Query(...),
    user: dict = Depends(get_current_user),
):
    return await svc_list_data_sources(business_id)


@router.post("/data-sources/connect")
async def connect_source(
    body: ConnectCallbackRequest,
    user: dict = Depends(get_current_user),
):
    return await svc_connect_data_source(body.business_id, body.source_type, body.details)


@router.post("/data-sources/disconnect")
async def disconnect_source(
    business_id: str = Query(...),
    source_type: str = Query(...),
    user: dict = Depends(get_current_user),
):
    return await svc_disconnect_data_source(business_id, source_type)
