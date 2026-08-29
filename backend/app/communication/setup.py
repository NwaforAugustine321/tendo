from __future__ import annotations

from app.communication.events import (
    EventDelivery,
)
from app.communication.interfaces import EventBus
from app.communication.subscribers.manager import (
    ApplicationEventManager,
)
from app.communication.subscribers.subscriber import (
    ApplicationEventSubscriber,
)
from app.communication.handlers.inapp_socket_forwarder_handler import (
    handle_inapp_socket_forwarder,
)
from app.communication.handlers.business_activities_persist_handler import (
    handle_business_persist_activties
)
from app.voice_agent.lifecycle import (
    voice_lifecycle_service,
)


def create_application_event_manager(
    event_bus: EventBus,
) -> ApplicationEventManager:

    manager = ApplicationEventManager()

    manager.register(
        ApplicationEventSubscriber(
            event_bus=event_bus,
            handler=handle_inapp_socket_forwarder,
            event_filter=lambda event: (
                event.delivery is EventDelivery.APP
            ),
            name="inapp_sockert_forwarder_subscriber",
        ),
    )

    manager.register(
        ApplicationEventSubscriber(
            event_bus=event_bus,
            handler=handle_business_persist_activties,
            event_filter=lambda event: (
                event.delivery is EventDelivery.APP
            ),
            name="business_activities_persist_subscriber",
        ),
    )

    manager.register(
        ApplicationEventSubscriber(
            event_bus=event_bus,
            handler=voice_lifecycle_service.handle,
            event_filter=lambda event: event.event in {
                "voice.session.requested",
                "voice.session.stop_requested",
            },
            name="voice-lifecycle-subscriber",
        ),
    )

    return manager
