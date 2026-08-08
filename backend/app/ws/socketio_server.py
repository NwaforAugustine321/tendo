

import logging
import socketio
from typing import Any

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=False,
    engineio_logger=False,
    ping_timeout=1800,
    ping_interval=25,
)

async def emit_event(event:str, sid:Any, payload: dict = {}):
    await sio.emit(event,payload,to=sid)