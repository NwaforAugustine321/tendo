"""WhatsApp adapter — Meta Cloud API for sending messages."""


async def send_text_message(phone: str, text: str) -> dict:
    """Send a text message via WhatsApp Cloud API."""
    # TODO: implement Meta API call
    return {"status": "sent"}


async def send_voice_message(phone: str, audio_url: str) -> dict:
    """Send a voice note via WhatsApp Cloud API."""
    # TODO: implement Meta API call
    return {"status": "sent"}
