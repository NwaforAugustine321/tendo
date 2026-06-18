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


async def send_input(websocket: WebSocket, input_spec: dict) -> None:
    """Send a structured input request (options or text field)."""
    await websocket.send_json({"type": "input", "data": input_spec})


async def send_message(websocket: WebSocket, text: str, questions: dict | None = None) -> None:
    """Send a complete agent message — text + optional questions."""
    msg: dict = {"type": "message", "data": {"response": text, "msg_type": "answer"}}
    if questions:
        msg["data"]["msg_type"] = "question"
        msg["data"]["questions"] = questions
    await websocket.send_json(msg)


async def send_turn_complete(websocket: WebSocket) -> None:
    """Signal that the current AI turn is complete."""
    await websocket.send_json({"type": "turn_complete"})


async def send_error(websocket: WebSocket, error: str) -> None:
    """Send an error message."""
    await websocket.send_json({"type": "error", "data": error})
