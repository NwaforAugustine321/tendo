"""Session context cache operations."""

import json

from app.redis.client import get_client

BCC_PREFIX = "bcc"
SESSION_PREFIX = "session"
BCC_TTL = 86400  # 24 hours
SESSION_TTL = 86400  # 24 hours


def get_business_context(business_id: str) -> dict | None:
    client = get_client()
    keys = [
        f"{BCC_PREFIX}:{business_id}:profile",
        f"{BCC_PREFIX}:{business_id}:understanding",
        f"{BCC_PREFIX}:{business_id}:entities",
        f"{BCC_PREFIX}:{business_id}:awareness",
        f"{BCC_PREFIX}:{business_id}:recent",
    ]
    result = {}
    for key in keys:
        data = client.get(key)
        if data:
            section = key.split(":")[-1]
            result[section] = json.loads(data)
    return result or None


def get_session_context(business_id: str, thread_id: str) -> dict | None:
    client = get_client()
    key = f"{SESSION_PREFIX}:{business_id}:{thread_id}:context"
    data = client.get(key)
    return json.loads(data) if data else None


def update_business_context(business_id: str, context: dict) -> None:
    client = get_client()
    for section, value in context.items():
        key = f"{BCC_PREFIX}:{business_id}:{section}"
        client.set(key, json.dumps(value), ex=BCC_TTL)


def update_session_context(business_id: str, thread_id: str, context: dict) -> None:
    client = get_client()
    key = f"{SESSION_PREFIX}:{business_id}:{thread_id}:context"
    client.set(key, json.dumps(context), ex=SESSION_TTL)
