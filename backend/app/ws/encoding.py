"""WebSocket encoding/decoding utilities for audio and binary data."""

import base64


def decode_audio(base64_data: str) -> bytes:
    """Decode base64-encoded audio data from a client message."""
    return base64.b64decode(base64_data)


def encode_audio(audio_bytes: bytes) -> str:
    """Encode raw audio bytes to base64 string for transport."""
    return base64.b64encode(audio_bytes).decode("utf-8")
