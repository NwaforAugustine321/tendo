"""Delivery tools — sendText and sendVoice for HTTP-based channels."""

from dataclasses import dataclass


@dataclass
class DeliveryResult:
    success: bool
    channel: str
    error: str | None = None


async def send_text(text: str, channel: str, user_id: str, thread_id: str) -> DeliveryResult:
    """Deliver text message to the specified channel."""
    # TODO: implement per-channel delivery
    return DeliveryResult(success=True, channel=channel)


async def send_voice(text: str, channel: str, user_id: str, thread_id: str) -> DeliveryResult:
    """Convert text to speech and deliver audio to the specified channel."""
    # TODO: call synthesize() then deliver audio
    return DeliveryResult(success=True, channel=channel)
