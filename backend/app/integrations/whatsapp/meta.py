"""Meta webhook verification helpers."""


def verify_challenge(hub_mode: str | None, hub_challenge: str | None, hub_verify_token: str | None) -> str | None:
    """Verify Meta webhook subscription. Returns challenge if valid."""
    if hub_mode == "subscribe" and hub_challenge:
        # TODO: validate hub_verify_token against configured secret
        return hub_challenge
    return None
