"""WebSocket receive operations — all inbound message methods."""

from typing import Any

from fastapi import WebSocket, WebSocketDisconnect


async def receive_json(websocket: WebSocket) -> dict[str, Any] | None:
    """
    Receive a JSON message from the client.
    Returns None on disconnect or error.
    """
    try:
        return await websocket.receive_json()
    except WebSocketDisconnect:
        return None
    except Exception:
        return None


async def receive_bytes(websocket: WebSocket) -> bytes | None:
    """
    Receive raw bytes from the client.
    Returns None on disconnect or error.
    """
    try:
        return await websocket.receive_bytes()
    except WebSocketDisconnect:
        return None
    except Exception:
        return None
