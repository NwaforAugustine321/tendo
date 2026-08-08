import logging
import base64
import httpx
from urllib.parse import urlencode
from app.config.settings import settings
from app.db.client import get_client
from app.db.tools.data_sources import get_business_id_by_phone_number, get_whatsapp_data_sources
from app.integrations.whatsapp.meta import verify_challenge, validate_signature
from app.integrations.whatsapp.normalizer import normalize
from app.integrations.whatsapp.models import ConfigurationError, NormalizedMessage
from app.record_knowledge.record_agent import process_record_content
from app.record_knowledge.models import RecordContentInput

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com"

test_access_token = settings.whatsapp_test_token
test_phone_number = 1249070458290584
test_wesa_id = 4002422153394266
mode = "testing"
modes_setting = ['testing']


async def _download_media_as_data_url(media_url: str, phone_number_id: str, mime_type: str | None) -> tuple[str, str]:
    """Download media from WhatsApp URL, upload to Supabase, return (data_url, file_url)."""
    try:
        sources = get_whatsapp_data_sources()
        access_token = None
        for row in sources:
            data = row.get("data") or {}
            if str(data.get("phone_number_id")) == str(phone_number_id):
                access_token = data.get("access_token")
                break

        if not access_token:
            access_token = test_access_token

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(media_url, headers={"Authorization": f"Bearer {access_token}"})
            resp.raise_for_status()
            file_bytes = resp.content

        mime = mime_type or "application/octet-stream"
        mime = mime.split(";")[0].strip()
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        data_url = f"data:{mime};base64,{b64}"

        # Upload to Supabase Storage
        import uuid
        ext = mime.split("/")[-1]
        file_name = f"whatsapp_media/{uuid.uuid4()}.{ext}"
        db = get_client()
        bucket_name = settings.bucket_name
        db.storage.from_(bucket_name).upload(file_name, file_bytes, {"content-type": mime})
        file_url = db.storage.from_(bucket_name).get_public_url(file_name)

        return data_url, file_url
    except Exception as e:
        logger.error(f"Failed to download media: {e}")
        return "", ""


def handle_whatsapp_verification(
    hub_mode: str | None,
    hub_challenge: str | None,
    hub_verify_token: str | None,
) -> tuple[int, str]:
    return verify_challenge(
        hub_mode=hub_mode,
        hub_challenge=hub_challenge,
        hub_verify_token=hub_verify_token,
        configured_token=settings.whatsapp_verify_token,
    )


async def handle_whatsapp_webhook(raw_body: bytes, signature: str | None, payload: dict) -> tuple[int, NormalizedMessage | None]:
    if not settings.whatsapp_app_secret:
        return 503, None

    try:
        valid = validate_signature(raw_body, signature, settings.whatsapp_app_secret)
    except ConfigurationError:
        return 503, None

    if not valid:
        return 401, None

    try:
        message = normalize(payload)
    except Exception:
        logger.error("WhatsApp normalizer error")
        return 200, None

    if message:
        logger.info("WhatsApp message received: %s", message.message_id)

        # Resolve business_id from webhook payload
        try:
            entry = payload["entry"][0]
            change = entry["changes"][0]
            value = change["value"]
            phone_number_id = value.get("metadata", {}).get("phone_number_id")

            business_id = get_business_id_by_phone_number(phone_number_id) if phone_number_id else None

            if business_id:
                content_type = message.message_type if message.message_type != "document" else "pdf"
                content = message.body or ""
                file_url = ""

                # For media messages, download bytes and convert to base64 data URL
                if message.media_url and content_type != "text":
                    data_url, file_url = await _download_media_as_data_url(message.media_url, phone_number_id, message.mime_type)
                    content = data_url
                    if not content:
                        logger.warning("Media download failed for message %s", message.message_id)

                if content:
                    logger.info("Processing %s content for business %s", content_type, business_id)
                    await process_record_content(RecordContentInput(
                        business_id=business_id,
                        record_id=None,
                        content_type=content_type,
                        content=content,
                        metadata={"source": "whatsapp", "file_url": file_url},
                    ))
                else:
                    logger.warning("No content to process for message %s", message.message_id)
            else:
                logger.warning("No business_id found for phone_number_id %s", phone_number_id)
        except Exception as e:
            logger.error("Failed to process WhatsApp message: %s", e, exc_info=True)

    return 200, message


async def list_data_sources(business_id: str) -> list[dict]:
    client = get_client()
    result = (
        client.table("data_sources")
        .select("*")
        .eq("business_id", business_id)
        .execute()
    )
    return result.data or []


async def connect_data_source(business_id: str, source_type: str, payload: dict) -> dict:
    client = get_client()
    data = {
        "business_id": business_id,
        "source_type": source_type,
        "status": "active",
        "data": payload,
        
    }
    result = (
        client.table("data_sources")
        .upsert(data, on_conflict="business_id,source_type")
        .execute()
    )
    return result.data[0] if result.data else data


async def disconnect_data_source(business_id: str, source_type: str) -> dict:
    client = get_client()
    client.table("data_sources").delete().eq("business_id", business_id).eq("source_type", source_type).execute()
    return {"status": "deleted"}


async def exchange_code_for_token(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        
        resp = await client.get(
            f"{GRAPH_API_BASE}/{settings.whatsapp_api_version}/oauth/access_token",
            params={
                "client_id": settings.whatsapp_app_id,
                "client_secret": settings.whatsapp_app_secret,
                "code": code
            },
        )
        data = resp.json()
        if resp.status_code != 200:
            logger.error("Token exchange failed: %s", data)
        return data


async def subscribe_to_waba(waba_id: str, access_token: str) -> bool:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GRAPH_API_BASE}/{settings.whatsapp_api_version}/{waba_id}/subscribed_apps",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        data = resp.json()
       
        return data.get("success", False)


async def onboard_whatsapp_business(
    business_id: str,
    code: str,
    waba_id: str | None = None,
    phone_number_id: str | None = None
) -> dict:

    if mode in modes_setting:
        await subscribe_to_waba(test_wesa_id, test_access_token)
        payload =  {
            "waba_id": test_wesa_id,
            "access_token": test_access_token,
            "phone_number_id":test_phone_number
        }
        return await connect_data_source(business_id, "whatsapp", payload)

    token_data = await exchange_code_for_token(code)
    access_token = token_data.get("access_token")
    if not access_token:
        logger.error("Failed to exchange code for token: %s", token_data)
        raise ValueError("Token exchange failed")

    if waba_id:
        await subscribe_to_waba(waba_id, access_token)
        logger.info("Subscribed to WABA %s", waba_id)

    payload = {
        "waba_id": waba_id,
        "access_token": access_token,
        "phone_number_id":phone_number_id
    }

    return await connect_data_source(business_id, "whatsapp", payload)
