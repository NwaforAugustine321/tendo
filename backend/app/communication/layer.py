"""Delivery decision layer — determines output format and delivers responses."""

from dataclasses import dataclass

from fastapi import WebSocket

from app.ws.sender import send_audio, send_transcript, send_turn_complete
from app.communication.delivery import DeliveryResult, send_text, send_voice


@dataclass
class DeliveryDecision:
    send_text_message: bool
    send_voice_message: bool


def decide_delivery(channel: str, input_type: str, user_preference: str) -> DeliveryDecision:
    """Determine delivery format based on channel and preferences."""
    if channel == "whatsapp":
        return DeliveryDecision(
            send_text_message=(input_type == "text"),
            send_voice_message=(input_type == "voice"),
        )

    if user_preference == "text_only":
        return DeliveryDecision(send_text_message=True, send_voice_message=False)
    elif user_preference == "voice_only":
        return DeliveryDecision(send_text_message=False, send_voice_message=True)
    else:
        return DeliveryDecision(send_text_message=True, send_voice_message=True)


async def deliver_response(
    text: str,
    channel: str,
    input_type: str,
    user_preference: str,
    user_id: str,
    thread_id: str,
) -> list[DeliveryResult]:
    """Deliver response via HTTP-based channels."""
    decision = decide_delivery(channel, input_type, user_preference)
    results: list[DeliveryResult] = []

    if decision.send_text_message:
        results.append(await send_text(text, channel, user_id, thread_id))

    if decision.send_voice_message:
        results.append(await send_voice(text, channel, user_id, thread_id))

    return results


async def deliver_response_ws(
    websocket: WebSocket,
    text: str,
    audio_bytes: bytes | None = None,
) -> None:
    """Deliver response via an active WebSocket connection."""
    if text:
        await send_transcript(websocket, text)

    if audio_bytes:
        await send_audio(websocket, audio_bytes)

    await send_turn_complete(websocket)
