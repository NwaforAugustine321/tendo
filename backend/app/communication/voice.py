"""Google Voice Engine integration — STT and TTS."""


async def transcribe(audio_bytes: bytes, timeout: float = 10.0) -> str:
    """Convert audio to text via Google Voice Engine STT."""
    # TODO: implement Google STT API call
    raise NotImplementedError("Voice transcription not yet implemented")


async def synthesize(text: str, timeout: float = 10.0) -> bytes:
    """Convert text to audio via Google Voice Engine TTS."""
    # TODO: implement Google TTS API call
    raise NotImplementedError("Voice synthesis not yet implemented")
