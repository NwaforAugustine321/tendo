"""Socket.IO voice event handlers — bridges Socket.IO to the voice session logic."""

import asyncio
import logging

from app.ws.socketio_server import sio
from app.config.settings import settings
from app.services.auth import handle_get_me, COOKIE_NAME

logger = logging.getLogger(__name__)

# Store active sessions
_sessions: dict[str, dict] = {}


@sio.event
async def connect(sid, environ, auth):
    """Handle new Socket.IO connection."""
    logger.info(f"Socket.IO connected: {sid}")

    # Extract query params from the connection
    query_string = environ.get('QUERY_STRING', '')
    params = dict(p.split('=', 1) for p in query_string.split('&') if '=' in p)

    session_id = params.get('session_id', '')
    business_id = params.get('business_id', '')

    # Auth from cookies
    cookies = environ.get('HTTP_COOKIE', '')
    token = None
    for cookie in cookies.split(';'):
        cookie = cookie.strip()
        if cookie.startswith(f'{COOKIE_NAME}='):
            token = cookie[len(f'{COOKIE_NAME}='):]
            break

    user_id = 'anonymous'
    if token:
        user = await handle_get_me(token)
        if user:
            user_id = user['user_id']
            logger.info(f"Socket.IO authenticated: user_id={user_id}")

    _sessions[sid] = {
        'session_id': session_id,
        'business_id': business_id,
        'user_id': user_id,
        'queue': asyncio.Queue(),  # Create queue immediately, before the task starts
    }

    # Start the voice session in background
    asyncio.create_task(_start_voice_session(sid, session_id, business_id, user_id))


@sio.event
async def message(sid, data):
    """Handle incoming messages from client."""
    session = _sessions.get(sid)
    if not session:
        return

    # Forward to the voice session message queue
    queue = session.get('queue')
    if queue:
        await queue.put(data)


@sio.event
async def disconnect(sid):
    """Handle Socket.IO disconnect."""
    logger.info(f"Socket.IO disconnected: {sid}")
    session = _sessions.pop(sid, None)
    # Don't signal None to queue — pipecat sessions persist for reconnects


async def _start_voice_session(sid: str, session_id: str, business_id: str, user_id: str):
    """Run the voice session for a connected client."""
    from app.communication.voice import run_voice_session

    # Reuse the queue created in connect() — avoids race condition with message events
    session_data = _sessions.get(sid, {})
    queue = session_data.get('queue') or asyncio.Queue()
    if sid in _sessions:
        _sessions[sid]['queue'] = queue

    async def send_to_client(msg: dict):
        await sio.emit('message', msg, to=sid)

    try:
        await run_voice_session(
            session_id=session_id,
            business_id=business_id,
            user_id=user_id,
            receive=queue.get,
            send=send_to_client,
        )
    except Exception as e:
        logger.error(f"Voice session error for {sid}: {e}", exc_info=True)
        await sio.emit('message', {'type': 'error', 'data': 'Something went wrong.'}, to=sid)
    finally:
        _sessions.pop(sid, None)
