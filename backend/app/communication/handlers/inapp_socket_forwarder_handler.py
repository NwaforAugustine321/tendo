from __future__ import annotations

import logging

from app.communication.events import ApplicationEvent
from app.communication.ws.server import (
    socket_dispatcher,
)

logger = logging.getLogger(__name__)


async def handle_inapp_socket_forwarder(
    event: ApplicationEvent,
) -> None:
    """
    Deliver an application event to the frontend.


    """

    user_id = ""

    if isinstance(
        event.data,
        dict,
    ):
        user_id = event.data.get(
            "user_id",
            "",
        )

    if not user_id:

        return

    await socket_dispatcher.emit_to_room(
        user_id=user_id,
        data=event.to_dict(),
    )
