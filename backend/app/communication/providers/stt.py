"""Custom streaming STT for LiveKit AgentSession."""

from __future__ import annotations

import asyncio
import logging
import queue
import threading

import riva.client
from livekit.agents import stt

from app.config.settings import settings

logger = logging.getLogger(__name__)

GRPC_URI = "grpc.nvcf.nvidia.com:443"


class Stt(stt.STT):

    def __init__(self, *, language: str = "multi", sample_rate: int = 16000) -> None:
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=True, interim_results=True),
        )
        self._language = language
        self._sample_rate = sample_rate

        metadata = [
            ("function-id", settings.stt_function_id),
            ("authorization", f"Bearer {settings.nvidia_api_key}"),
        ]
        auth = riva.client.Auth(uri=GRPC_URI, use_ssl=True, metadata_args=metadata)
        self._asr_service = riva.client.ASRService(auth)

    async def _recognize_impl(self, buffer, *, language=None, conn_options=None) -> stt.SpeechEvent:
        audio_bytes = bytes(buffer) if not isinstance(buffer, bytes) else buffer
        config = riva.client.RecognitionConfig(
            language_code=language or self._language,
            max_alternatives=1,
            enable_automatic_punctuation=True,
            encoding=riva.client.AudioEncoding.LINEAR_PCM,
            sample_rate_hertz=self._sample_rate,
            audio_channel_count=1,
        )
        response = await asyncio.to_thread(
            self._asr_service.offline_recognize, audio_bytes, config
        )
        transcript = ""
        if response.results:
            for result in response.results:
                if result.alternatives:
                    transcript += result.alternatives[0].transcript
        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(text=transcript.strip(), language=language or self._language)],
        )

    def stream(self, *, language=None, conn_options=None) -> "SttStream":
        return SttStream(
            stt_instance=self,
            conn_options=conn_options,
            asr_service=self._asr_service,
            language=language or self._language,
            sample_rate=self._sample_rate,
        )


class SttStream(stt.SpeechStream):

    def __init__(self, *, stt_instance, conn_options, asr_service, language: str, sample_rate: int) -> None:
        from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
        super().__init__(stt=stt_instance, conn_options=conn_options or DEFAULT_API_CONNECT_OPTIONS, sample_rate=sample_rate)
        self._asr_service = asr_service
        self._language = language
        self._sample_rate = sample_rate

    async def _run(self) -> None:
        streaming_config = riva.client.StreamingRecognitionConfig(
            config=riva.client.RecognitionConfig(
                language_code=self._language,
                max_alternatives=1,
                enable_automatic_punctuation=True,
                encoding=riva.client.AudioEncoding.LINEAR_PCM,
                sample_rate_hertz=self._sample_rate,
                audio_channel_count=1,
            ),
            interim_results=True,
        )

        audio_q: queue.Queue[bytes | None] = queue.Queue()
        result_q: asyncio.Queue[stt.SpeechEvent | None] = asyncio.Queue()

        def audio_generator():
            while True:
                chunk = audio_q.get()
                if chunk is None:
                    break
                yield chunk

        def run_streaming():
            try:
                responses = self._asr_service.streaming_response_generator(
                    audio_chunks=audio_generator(),
                    streaming_config=streaming_config,
                )
                for response in responses:
                    if not response.results:
                        continue
                    for result in response.results:
                        if not result.alternatives:
                            continue
                        transcript = result.alternatives[0].transcript.strip()
                        if not transcript:
                            continue
                        event = stt.SpeechEvent(
                            type=stt.SpeechEventType.FINAL_TRANSCRIPT if result.is_final else stt.SpeechEventType.INTERIM_TRANSCRIPT,
                            alternatives=[stt.SpeechData(text=transcript, language=self._language)],
                        )
                        result_q.put_nowait(event)
            except Exception as e:
                logger.error(f"[Stt] streaming error: {e}")
            finally:
                result_q.put_nowait(None)

        thread = threading.Thread(target=run_streaming, daemon=True)
        thread.start()

        async def feed_audio():
            try:
                async for frame in self._input_ch:
                    if isinstance(frame, self._FlushSentinel):
                        continue
                    audio_q.put(frame.data.tobytes())
            except Exception:
                pass
            finally:
                audio_q.put(None)

        async def read_results():
            while True:
                event = await result_q.get()
                if event is None:
                    break
                self._event_ch.send_nowait(event)

        feed_task = asyncio.ensure_future(feed_audio())
        read_task = asyncio.ensure_future(read_results())

        try:
            await asyncio.gather(feed_task, read_task)
        except Exception as e:
            logger.error(f"[Stt] run error: {e}")
        finally:
            audio_q.put(None)
            feed_task.cancel()
            read_task.cancel()
