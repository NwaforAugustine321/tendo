from __future__ import annotations

from app.communication.config import EventBusConfig
from app.communication.provider import EventBusProvider
from app.communication.transports.socketio import (
    SocketIOTransport,
)
from app.communication.ws.dispatcher import (
    SocketDispatcher,
)
from app.communication.ws.registry import (
    SocketConnectionRegistry,
)
from app.config import settings


event_bus_provider = EventBusProvider(
    EventBusConfig(
        channel="application.events",
        options={
            "url": settings.redis_url,
        },
    ),
)

event_bus = event_bus_provider.get()

redis_transport = event_bus_provider.get_transport()


socketio_transport = SocketIOTransport()

sio = socketio_transport.sio


connection_registry = SocketConnectionRegistry(
    connection_store=redis_transport,
)


socket_dispatcher = SocketDispatcher(
    connection_store=redis_transport,
    transport=socketio_transport,
)
