"""Payload normalizer — transforms webhook payload to event format."""


def normalize(payload: dict) -> dict | None:
    """
    Transform a webhook payload into unified event fields.
    Returns None if the payload is not a user message.
    """
    # TODO: parse webhook structure
    return None
