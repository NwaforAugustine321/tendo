from __future__ import annotations

import logging

from app.communication.events import ApplicationEvent
from app.communication.ws.server import (
    socket_dispatcher,
)

logger = logging.getLogger(__name__)


async def handle_business_persist_activties(
    event: ApplicationEvent,
) -> None:
    """
     Persist business activities to long term storage for further process with bla agent
    """

    busines_id = ""

    if isinstance(
        event.data,
        dict,
    ):
        busines_id = event.data.get(
            "busines_id",
            "",
        )

    if not busines_id:

        return

    print(event)
