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
from app.communication.handlers.frontend_handler import (
    handle_frontend_event,
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
            handler=handle_frontend_event,
            event_filter=lambda event: (
                event.delivery is EventDelivery.APP
            ),
            name="frontend-event-subscriber",
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
