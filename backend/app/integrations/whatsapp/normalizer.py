"""WhatsApp payload normalizer — transforms webhook payload to UnifiedUserEvent."""


def normalize(payload: dict) -> dict | None:
    """
    Transform a Meta WhatsApp webhook payload into UnifiedUserEvent fields.
    Returns None if the payload is not a user message.
    """
    # TODO: parse Meta webhook structure
    # entry → changes → value → messages → [0]
    return None
