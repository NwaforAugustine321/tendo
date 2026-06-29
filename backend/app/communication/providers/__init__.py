"""Voice providers — pluggable TTS/STT backends."""

import logging

from app.communication.providers.base import VoiceProvider

logger = logging.getLogger(__name__)

_SUPPORTED_PROVIDERS = ("google", "cartesia")


def create_voice_provider() -> VoiceProvider:
    """Create the configured voice provider instance.

    Reads settings.voice_provider to determine which backend to use:
    - "cartesia": Cartesia TTS+STT with multilingual WebSocket streaming
    - "google" (default): Google Gemini Live API

    Returns:
        A VoiceProvider instance ready to be connected.

    Raises:
        ValueError: If the configured provider name is not supported.
    """
    from app.config.settings import settings

    provider_name = (settings.voice_provider or "google").lower().strip()

    if provider_name not in _SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported voice provider: '{provider_name}'. "
            f"Must be one of: {', '.join(_SUPPORTED_PROVIDERS)}"
        )

    if provider_name == "cartesia":
        from app.communication.providers.cartesia_provider import CartesiaVoiceProvider

        logger.info("Initializing Cartesia voice provider")
        return CartesiaVoiceProvider()

    # Default: Google Gemini Live API
    from app.communication.providers.google_provider import GoogleVoiceProvider

    logger.info("Initializing Google voice provider")
    return GoogleVoiceProvider()


__all__ = ["VoiceProvider", "create_voice_provider"]
