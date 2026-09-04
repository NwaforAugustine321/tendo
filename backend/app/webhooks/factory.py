from ..config.settings import settings
from .client import WebhookClient, WebhookConfig
from .contracts import (
    HOOKS
)

global _webhook_client

_webhook_client = WebhookClient(
    hooks={
        f"{HOOKS.VOICE_AGENT}": WebhookConfig(
            url=settings.voice_agent_webhook_url,
            secret=settings.webhook_internal_secret,
            timeout=settings.webhook_default_timeout,
        ),
    },
)


def get_webhook_client():
    return _webhook_client
