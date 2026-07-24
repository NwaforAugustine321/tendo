"""Socket.IO server — replaces raw WebSocket handling."""

import logging
import socketio

logger = logging.getLogger(__name__)

# Create Socket.IO server with CORS
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=False,
    engineio_logger=False,
    ping_timeout=120,
    ping_interval=30,
)
