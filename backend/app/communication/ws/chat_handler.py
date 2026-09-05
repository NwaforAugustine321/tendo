from __future__ import annotations

import logging

from app.communication.ws.models import (
    SocketConnection,
    SocketTextInput,
)
from app.communication.ws.server import (
    connection_registry,
    sio,
    socket_dispatcher,
)
from app.graph.nodes.moa_orchestrator import moa_node
from app.services.auth import COOKIE_NAME, handle_get_me
from app.communication.events import ApplicationEvent
from app.communication.event_bus import get_event_bus
from app.communication.events import EventDelivery

logger = logging.getLogger(__name__)


@sio.event
async def connect(
    sid,
    environ,
    auth,
):
    """
    Register a Socket.IO connection.

    The socket connects at login time. Only user identity (from the
    auth cookie) is resolved here. Business and session context are
    provided per-message by the chat panel.
    """

    cookies = environ.get(
        "HTTP_COOKIE",
        "",
    )

    token = None

    for cookie in cookies.split(";"):
        cookie = cookie.strip()

        if cookie.startswith(
            f"{COOKIE_NAME}=",
        ):
            token = cookie[
                len(f"{COOKIE_NAME}="):
            ]
            break

    user_id = ""

    if token:
        try:
            user = await handle_get_me(
                token,
            )

            if user:
                user_id = user["user_id"]
        except Exception as exc:
            logger.error(
                "Socket.IO connect: failed to resolve user from token: %s",
                exc,
            )
            user_id = ""

    connection = SocketConnection(
        sid=sid,
        user_id=user_id,
    )

    await connection_registry.register(
        connection,
    )

    logger.info(
        "Socket.IO connected and registered: "
        "sid=%s user_id=%s",
        sid,
        user_id,
    )


@sio.event
async def socket_heartbeat(
    sid,
):
    """
    Refresh the Redis expiration for an active Socket.IO connection.

    The frontend sends this periodically while the connection is
    active. Redis automatically removes the SID when heartbeats stop.
    """

    refreshed = await connection_registry.refresh(
        sid,
    )

    if not refreshed:
        logger.debug(
            "Socket heartbeat received for inactive SID: %s",
            sid,
        )


@sio.event
async def message(
    sid,
    data,
):
    """Handle an incoming Socket.IO message."""

    logger.info(
        "Socket.IO message event received: sid=%s",
        sid,
    )

    connection = await connection_registry.get(
        sid,
    )

    if connection is None:
        logger.error(
            "Message received from unregistered connection: sid=%s",
            sid,
        )
        return

    if not isinstance(
        data,
        dict,
    ):
        payload = {
            "type": "error",
            "payload": {
                "message": "Invalid message format",
            },
            "user_id": user_id,
        }

        await get_event_bus().publish(
            ApplicationEvent(
                event="error",
                source="agent",
                delivery=EventDelivery.APP,
                data=payload,
            ),
        )
        return

    message_type = data.get(
        "type",
        "",
    )

    if message_type != "text":
        payload = {
            "type": "error",
            "payload": {
                "message": "Invalid message type",
            },
            "user_id": user_id,
        }

        await get_event_bus().publish(
            ApplicationEvent(
                event="error",
                source="agent",
                delivery=EventDelivery.APP,
                data=payload,
            ),
        )
        return

    raw_payload = data.get(
        "payload",
    )

    if not isinstance(
        raw_payload,
        dict,
    ):
        payload = {
            "type": "error",
            "payload": {
                "message": "Invalid message payload"
            },
            "user_id": user_id,
        }

        await get_event_bus().publish(
            ApplicationEvent(
                event="error",
                source="agent",
                delivery=EventDelivery.APP,
                data=payload,
            ),
        )
        return

    text_input = SocketTextInput.from_dict(
        raw_payload,
    )

    if not text_input.content.strip():
        return

    business_id = text_input.business_id
    session_id = text_input.session_id
    user_id = connection.user_id

    if not user_id:
        payload = {
            "type": "error",
            "payload": {
                "message": "Unauthorized, no user id",
            },
            "user_id": user_id,
        }

        await get_event_bus().publish(
            ApplicationEvent(
                event="error",
                source="agent",
                delivery=EventDelivery.APP,
                data=payload,
            ),
        )
        return

    if not business_id:
        payload = {
            "type": "error",
            "payload": {
                "message": "Unauthorized, no business id"
            },
            "user_id": user_id,
        }

        await get_event_bus().publish(
            ApplicationEvent(
                event="error",
                source="agent",
                delivery=EventDelivery.APP,
                data=payload,
            ),
        )
        return

    if not session_id:
        payload = {
            "type": "error",
            "payload": {
                "message": "Unauthorized, no session id"
            },
            "user_id": user_id,
        }

        await get_event_bus().publish(
            ApplicationEvent(
                event="error",
                source="agent",
                delivery=EventDelivery.APP,
                data=payload,
            ),
        )
        return

    logger.info(
        "Chat message from %s: %s",
        sid,
        text_input.content[:100],
    )

    try:
        graph_state = {
            "text": text_input.content,
            "record_id": text_input.record_id,
            "business_id": business_id,
            "thread_id": session_id,
            "session_id": session_id,
            "user_id": user_id,
        }

        result = await moa_node(
            graph_state,
        )

        response = result.get(
            "response",
            {},
        )

        payload = {
            "type": "message",
            "payload": {
                "message": response.get(
                    "text",
                    "",
                ),
            },
            "user_id": user_id,
        }

        await get_event_bus().publish(
            ApplicationEvent(
                event="message",
                source="agent",
                delivery=EventDelivery.APP,
                data=payload,
            ),
        )

    except Exception as exc:
        logger.error(
            "Chat error for %s: %s",
            sid,
            exc,
            exc_info=True,
        )

        payload = {
            "type": "message",
            "payload": {
                "message": "Something went wrong. Please try again.",
            },
            "user_id": user_id,
        }

        await get_event_bus().publish(
            ApplicationEvent(
                event="message",
                source="agent",
                delivery=EventDelivery.APP,
                data=payload,
            ),
        )


@sio.event
async def disconnect(
    sid,
    reason=None,
):
    """
    Remove a disconnected Socket.IO connection.

    python-socketio passes a disconnect reason to this handler, so
    the parameter is accepted and optional for older versions.
    """

    logger.info(
        "Socket.IO disconnected: %s (%s)",
        sid,
        reason or "unknown reason",
    )

    try:
        await connection_registry.remove(
            sid,
        )

    except Exception as exc:
        # Cleanup is best effort. Connection entries carry a TTL,
        # so a failed removal expires on its own.
        logger.warning(
            "Failed to clean up Socket.IO connection %s: %s",
            sid,
            exc,
        )
