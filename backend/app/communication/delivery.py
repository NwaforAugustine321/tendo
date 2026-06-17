"""Communication delivery tools — sendText and sendVoice."""

from dataclasses import dataclass


@dataclass
class DeliveryResult:
    success: bool
    channel: str
    error: str | None = None


async def send_text(text: str, channel: str, user_id: str, thread_id: str) -> DeliveryResult:
    """Deliver text message to Web, Mobile, or WhatsApp."""
    # TODO: implement per-channel delivery
    return DeliveryResult(success=True, channel=channel)


async def send_voice(text: str, channel: str, user_id: str, thread_id: str) -> DeliveryResult:
    """Convert text to speech and deliver audio to the appropriate channel."""
    # TODO: call voice.synthesize() then deliver audio
    return DeliveryResult(success=True, channel=channel)
