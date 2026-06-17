"""WebSocket send operations — all outbound message methods."""

from typing import Any

from fastapi import WebSocket

from app.ws.encoding import encode_audio


async def send_json(websocket: WebSocket, msg: dict[str, Any]) -> None:
    """Send a raw JSON message."""
    await websocket.send_json(msg)


async def send_audio(websocket: WebSocket, audio_bytes: bytes) -> None:
    """Send audio data as a base64-encoded PCM message."""
    await websocket.send_json({
        "type": "audio",
        "data": encode_audio(audio_bytes),
    })


async def send_transcript(websocket: WebSocket, text: str) -> None:
    """Send a text transcript message."""
    await websocket.send_json({"type": "transcript", "data": text})


async def send_turn_complete(websocket: WebSocket) -> None:
    """Signal that the current AI turn is complete."""
    await websocket.send_json({"type": "turn_complete"})


async def send_error(websocket: WebSocket, error: str) -> None:
    """Send an error message."""
    await websocket.send_json({"type": "error", "data": error})
