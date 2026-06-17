"""Response Delivery Decision Layer — determines output format based on channel + preferences."""

from app.communication.delivery import DeliveryResult, send_text, send_voice


async def deliver_response(
    text: str,
    channel: str,
    input_type: str,
    user_preference: str,
    user_id: str,
    thread_id: str,
) -> list[DeliveryResult]:
    """
    Decide final output format and deliver.

    App rules (based on user_preference):
      - voice_text (default): sendText + sendVoice
      - text_only: sendText
      - voice_only: sendVoice

    WhatsApp rules (mirrors input_type):
      - text input → sendText
      - voice input → sendVoice
    """
    results: list[DeliveryResult] = []

    if channel == "whatsapp":
        if input_type == "voice":
            results.append(await send_voice(text, channel, user_id, thread_id))
        else:
            results.append(await send_text(text, channel, user_id, thread_id))
    else:
        # App channel — use user preference
        if user_preference in ("voice_text", ""):
            results.append(await send_text(text, channel, user_id, thread_id))
            results.append(await send_voice(text, channel, user_id, thread_id))
        elif user_preference == "text_only":
            results.append(await send_text(text, channel, user_id, thread_id))
        elif user_preference == "voice_only":
            results.append(await send_voice(text, channel, user_id, thread_id))

    return results
