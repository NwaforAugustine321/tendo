"""Meta webhook verification helpers."""

import hmac
import hashlib

from app.integrations.whatsapp.models import ConfigurationError


def verify_challenge(
    hub_mode: str | None,
    hub_challenge: str | None,
    hub_verify_token: str | None,
    configured_token: str,
) -> tuple[int, str]:
    """Verify Meta webhook subscription challenge."""
    if not configured_token:
        return (503, "")
    if hub_mode != "subscribe":
        return (403, "")
    if hub_verify_token != configured_token:
        return (403, "")
    if hub_challenge is None:
        return (400, "")
    return (200, hub_challenge)


def validate_signature(raw_body: bytes, signature_header: str | None, app_secret: str) -> bool:
    """Validate X-Hub-Signature-256 header against the raw body."""
    if not app_secret:
        raise ConfigurationError("WHATSAPP_APP_SECRET is not configured")

    if signature_header is None or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        app_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    received = signature_header[len("sha256="):]
    return hmac.compare_digest(expected, received)
