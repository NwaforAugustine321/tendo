"""WebSocket connection lifecycle management."""

from fastapi import WebSocket, WebSocketDisconnect


async def accept(websocket: WebSocket) -> None:
    """Accept an incoming WebSocket connection."""
    await websocket.accept()


async def close(websocket: WebSocket) -> None:
    """Safely close a WebSocket connection."""
    try:
        await websocket.close()
    except Exception:
        pass


def is_open(websocket: WebSocket) -> bool:
    """Check if the WebSocket connection is still open."""
    return websocket.client_state.name == "CONNECTED"
