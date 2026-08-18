from __future__ import annotations

import logging

from app.communication.ws.models import (
    SocketConnection,
    SocketMessage,
    SocketResponse,
    SocketTextInput,
)
from app.communication.ws.server import (
    connection_registry,
    sio,
    socket_dispatcher,
)
from app.graph.nodes.moa_orchestrator import moa_node
from app.services.auth import COOKIE_NAME, handle_get_me

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
        await socket_dispatcher.emit_to_sid(
            sid=sid,
            event="message",
            payload=SocketMessage(
                type="error",
                payload=SocketResponse(
                    content="Invalid message format",
                ),
            ).to_dict()
        )
        return

    message_type = data.get(
        "type",
        "",
    )

    if message_type != "text":
        await socket_dispatcher.emit_to_sid(
            sid=sid,
            event="message",
            payload=SocketMessage(
                type="error",
                payload=SocketResponse(
                    content="Invalid message type",
                ),
            ).to_dict()
        )
        return

    raw_payload = data.get(
        "payload",
    )

    if not isinstance(
        raw_payload,
        dict,
    ):
        await socket_dispatcher.emit_to_sid(
            sid=sid,
            event="message",
            payload=SocketMessage(
                type="error",
                payload=SocketResponse(
                    content="Invalid message payload",
                ),
            ).to_dict()
        )
        return

    text_input = SocketTextInput.from_dict(
        raw_payload,
    )

    if not text_input.content.strip():
        return

    # business_id and session_id come from the message payload.
    business_id = text_input.business_id
    session_id = text_input.session_id
    user_id = connection.user_id

    if not user_id:
        await socket_dispatcher.emit_to_sid(
            sid=sid,
            event="message",
            payload=SocketMessage(
                type="error",
                payload=SocketResponse(
                    content="Unauthorized, no user id",
                ),
            ).to_dict()
        )
        return

    if not business_id:
        await socket_dispatcher.emit_to_sid(
            sid=sid,
            event="message",
            payload=SocketMessage(
                type="error",
                payload=SocketResponse(
                    content="Unauthorized, no business id",
                ),
            ).to_dict()
        )
        return

    if not session_id:
        await socket_dispatcher.emit_to_sid(
            sid=sid,
            event="message",
            payload=SocketMessage(
                type="error",
                payload=SocketResponse(
                    content="Unauthorized, no session id",
                ),
            ).to_dict()
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

        await socket_dispatcher.emit_to_sid(
            sid=sid,
            event="message",
            payload={
                "data": {
                    "type": "message",
                    "payload": {
                        "content": response.get(
                            "text",
                            "",
                        ),
                    },
                },
            },
        )

    except Exception as exc:
        logger.error(
            "Chat error for %s: %s",
            sid,
            exc,
            exc_info=True,
        )

        await socket_dispatcher.emit_to_sid(
            sid=sid,
            event="message",
            payload=SocketMessage(
                type="message",
                payload=SocketResponse(
                    content=(
                        "Something went wrong. "
                        "Please try again."
                    ),
                ),
            ).to_dict()
        )


@sio.event
async def disconnect(
    sid,
):
    """Remove a disconnected Socket.IO connection."""

    logger.info(
        "Socket.IO disconnected: %s",
        sid,
    )

    await connection_registry.remove(
        sid,
    )
