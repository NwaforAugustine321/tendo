"""Adapter for sending messages via the messaging API."""


async def send_text_message(phone: str, text: str) -> dict:
    """Send a text message."""
    # TODO: implement API call
    return {"status": "sent"}


async def send_voice_message(phone: str, audio_url: str) -> dict:
    """Send a voice note."""
    # TODO: implement API call
    return {"status": "sent"}
