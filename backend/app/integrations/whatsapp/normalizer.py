
from app.integrations.whatsapp.models import NormalizedMessage

def normalize(payload: dict) -> NormalizedMessage | None:
    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]
        value = change["value"]
    except (KeyError, IndexError, TypeError):
        return None

    if "statuses" in value:
        return None

    messages = value.get("messages")
    if not messages:
        return None

    msg = messages[0]

    sender = msg.get("from")
    message_id = msg.get("id")
    timestamp_raw = msg.get("timestamp")

    if not sender or not message_id or not timestamp_raw:
        return None

    try:
        timestamp = int(timestamp_raw)
    except (ValueError, TypeError):
        return None

    msg_type = msg.get("type")

    if msg_type == "text":
        text_obj = msg.get("text")
        if not text_obj:
            return None
        body = text_obj.get("body", "")[:4096]
        return NormalizedMessage(
            sender=sender,
            message_id=message_id,
            timestamp=timestamp,
            message_type="text",
            body=body,
        )

    if msg_type == "audio":
        audio_obj = msg.get("audio")
        if not audio_obj:
            return None
        return NormalizedMessage(
            sender=sender,
            message_id=message_id,
            timestamp=timestamp,
            message_type="audio",
            media_id=audio_obj.get("id"),
            mime_type=audio_obj.get("mime_type"),
            media_url=audio_obj.get("url"),
        )

    if msg_type == "image":
        image_obj = msg.get("image")
        if not image_obj:
            return None
        return NormalizedMessage(
            sender=sender,
            message_id=message_id,
            timestamp=timestamp,
            message_type="image",
            media_id=image_obj.get("id"),
            mime_type=image_obj.get("mime_type"),
            media_url=image_obj.get("url"),
            body=image_obj.get("caption"),
        )

    if msg_type == "document":
        doc_obj = msg.get("document")
        if not doc_obj:
            return None
        return NormalizedMessage(
            sender=sender,
            message_id=message_id,
            timestamp=timestamp,
            message_type="document",
            media_id=doc_obj.get("id"),
            mime_type=doc_obj.get("mime_type"),
            media_url=doc_obj.get("url"),
            filename=doc_obj.get("filename"),
            body=doc_obj.get("caption"),
        )

    return None
