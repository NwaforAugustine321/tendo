from __future__ import annotations

import base64
import logging
import os
import tempfile

from app.config.settings import settings
from app.runtime.rag.models import (
    RAGDocument,
)

from ..loader import (
    DocumentLoader,
)

logger = logging.getLogger(__name__)


class AudioLoader(
    DocumentLoader,
):
    """
    Loads audio by transcribing it using NVIDIA
    Riva ASR.

    The audio should be supplied as a data URL.
    """

    async def load(
        self,
        *,
        source,
    ) -> list[RAGDocument]:

        if not source:
            return []

        source = str(source)

        # Handle HTTP(S) URLs — download and convert to data URL.
        if source.startswith("http://") or source.startswith("https://"):
            logger.info(f"AudioLoader: downloading from URL: {source[:80]}")
            source = await self._download_as_data_url(source)
            logger.info(
                f"AudioLoader: data URL length after download: {len(source)}")
            if not source:
                return []

        if not source.startswith(
            "data:audio",
        ):
            return []

        transcript = await self._transcribe(
            source,
        )

        if not transcript.strip():
            return []

        return [
            RAGDocument(
                id="",
                title="",
                source="audio",
                content=transcript,
                metadata={"source_type": "audio"},
            )
        ]

    async def _transcribe(
        self,
        audio_data_url: str,
    ) -> str:
        """
        Transcribe audio data URL using NVIDIA
        Riva ASR.
        """

        import riva.client

        try:

            _, b64_data = audio_data_url.split(
                ",",
                1,
            )

            audio_bytes = base64.b64decode(
                b64_data,
            )

            with tempfile.NamedTemporaryFile(
                suffix=".raw",
                delete=False,
            ) as tmp:

                tmp.write(
                    audio_bytes,
                )

                tmp_path = tmp.name

            wav_path = tmp_path + ".wav"

            try:

                import subprocess

                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        tmp_path,
                        "-ar",
                        "16000",
                        "-ac",
                        "1",
                        "-f",
                        "wav",
                        wav_path,
                    ],
                    capture_output=True,
                    timeout=60,
                )

            except (
                FileNotFoundError,
                subprocess.TimeoutExpired,
            ):

                wav_path = tmp_path

            try:

                metadata = [
                    (
                        "function-id",
                        "71203149-d3b7-4460-8231-1be2543a1fca",
                    ),
                    (
                        "authorization",
                        f"Bearer {settings.nvidia_api_key}",
                    ),
                ]

                auth = riva.client.Auth(
                    uri="grpc.nvcf.nvidia.com:443",
                    use_ssl=True,
                    metadata_args=metadata,
                )

                asr_service = (
                    riva.client.ASRService(
                        auth,
                    )
                )

                with open(
                    wav_path,
                    "rb",
                ) as file:

                    audio_content = file.read()

                AUDIO_CHUNK_SIZE = 960000
                AUDIO_OVERLAP_SIZE = 32000

                config = (
                    riva.client.RecognitionConfig(
                        language_code="en-US",
                        max_alternatives=1,
                        enable_automatic_punctuation=True,
                        encoding=riva.client.AudioEncoding.LINEAR_PCM,
                        sample_rate_hertz=16000,
                        audio_channel_count=1,
                    )
                )

                if (
                    len(audio_content)
                    <= AUDIO_CHUNK_SIZE + 44
                ):

                    response = (
                        asr_service.offline_recognize(
                            audio_content,
                            config,
                        )
                    )

                    transcript_parts: list[str] = []

                    for result in response.results:

                        if result.alternatives:

                            transcript_parts.append(
                                result.alternatives[
                                    0
                                ].transcript,
                            )

                    return " ".join(
                        transcript_parts,
                    )

                wav_header = audio_content[:44]

                raw_audio = audio_content[44:]

                transcripts: list[str] = []

                offset = 0

                while offset < len(raw_audio):

                    chunk = raw_audio[
                        offset: offset
                        + AUDIO_CHUNK_SIZE
                    ]

                    chunk_with_header = (
                        wav_header + chunk
                    )

                    try:

                        response = (
                            asr_service.offline_recognize(
                                chunk_with_header,
                                config,
                            )
                        )

                        for result in response.results:

                            if result.alternatives:

                                transcripts.append(
                                    result.alternatives[
                                        0
                                    ].transcript,
                                )

                    except Exception as error:

                        logger.warning(
                            "Chunk transcription failed "
                            "at offset %s: %s",
                            offset,
                            error,
                        )

                    offset += (
                        AUDIO_CHUNK_SIZE
                        - AUDIO_OVERLAP_SIZE
                    )

                return " ".join(
                    transcripts,
                )

            finally:

                os.unlink(
                    tmp_path,
                )

                if (
                    wav_path != tmp_path
                    and os.path.exists(
                        wav_path,
                    )
                ):
                    os.unlink(
                        wav_path,
                    )

        except Exception as error:

            logger.warning(
                "Audio transcription failed: %s",
                error,
            )

            return ""

    async def _download_as_data_url(
        self,
        url: str,
    ) -> str:
        """
        Download an audio file from a URL and convert
        to a data URL for transcription.
        """

        import httpx

        try:

            async with httpx.AsyncClient(
                timeout=120.0,
            ) as client:

                response = await client.get(url)
                response.raise_for_status()

            content_type = response.headers.get(
                "content-type",
                "audio/mpeg",
            )

            b64 = base64.b64encode(
                response.content,
            ).decode("utf-8")

            return f"data:{content_type};base64,{b64}"

        except Exception as error:

            logger.warning(
                "Failed to download audio from URL: %s",
                error,
            )

            return ""
