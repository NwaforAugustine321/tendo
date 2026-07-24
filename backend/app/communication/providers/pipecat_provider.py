"""Pipecat NVIDIA NIM voice provider.

Pipeline:
    Audio In → WakeCheckFilter (optional) → NvidiaSTTService (Parakeet)
    → TendoLLMProcessor → NvidiaTTSService (Magpie) → SocketIOOutputTransport

Sessions are kept alive across reconnects — the pipeline is created once per
session_id and reused, avoiding the 2s STT/TTS re-initialization cost.
"""

import asyncio
import logging

from pipecat.frames.frames import (
    EndFrame,
    InputAudioRawFrame,
    StartFrame,
    TextFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
    TTSStoppedFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.filters.wake_check_filter import WakeCheckFilter
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.nvidia.stt import NvidiaSTTService
from pipecat.services.nvidia.tts import NvidiaTTSService

from app.config.settings import settings
from app.ws.encoding import decode_audio, encode_audio

logger = logging.getLogger(__name__)

# Persistent pipeline sessions — keyed by session_id
_pipeline_sessions: dict[str, "_PipelineSession"] = {}


class _PipelineSession:
    """Holds a running Pipecat pipeline for one voice session."""

    def __init__(self, session_id: str, business_id: str, user_id: str):
        self.session_id = session_id
        self.business_id = business_id
        self.user_id = user_id
        self.send = None
        self.queue: asyncio.Queue = asyncio.Queue()
        self.task: PipelineTask | None = None
        self._runner_task: asyncio.Task | None = None

    def update_send(self, send):
        """Swap in the new send function after a reconnect."""
        self.send = send
        if self.task:
            self.task.set_callbacks({})  # output transport holds ref to send

    def is_running(self) -> bool:
        return self._runner_task is not None and not self._runner_task.done()


async def run_pipecat_session(
    session_id: str,
    business_id: str,
    user_id: str,
    receive,
    send,
) -> None:
    """Run or resume a Pipecat pipeline session."""

    existing = _pipeline_sessions.get(session_id)

    if existing and existing.is_running():
        logger.info(f"Pipecat: resuming existing pipeline for session {session_id[:8]}")
        existing.send = send
        await send({"type": "turn_complete"})
        await _pump_queue(existing.queue, receive)
        return

    # New session — create pipeline
    session = _PipelineSession(session_id, business_id, user_id)
    session.send = send
    _pipeline_sessions[session_id] = session

    output_transport = SocketIOOutputTransport(session=session, sample_rate=settings.nvidia_nim_sample_rate)

    stt = NvidiaSTTService(
        api_key=settings.nvidia_api_key,
        model=settings.nvidia_nim_asr_model,
        sample_rate=16000,
    )

    tts = NvidiaTTSService(
        api_key=settings.nvidia_api_key,
        model=settings.nvidia_nim_tts_model,
        voice=settings.nvidia_nim_tts_voice,
        sample_rate=settings.nvidia_nim_sample_rate,
    )

    llm_processor = TendoLLMProcessor(session=session)

    processors = [stt, llm_processor, tts, output_transport]

    if settings.nvidia_nim_wake_word.strip():
        processors.insert(0, WakeCheckFilter(wake_phrases=[settings.nvidia_nim_wake_word.strip()]))

    pipeline = Pipeline(processors)

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=False,
            send_initial_empty_metrics=False,
        ),
    )
    session.task = task

    runner = PipelineRunner()

    await send({"type": "turn_complete"})

    async def _run_pipeline():
        asyncio.create_task(_feed_queue(task, session.queue))
        try:
            await runner.run(task)
        finally:
            _pipeline_sessions.pop(session_id, None)
            logger.info(f"Pipecat: pipeline ended for session {session_id[:8]}")

    session._runner_task = asyncio.create_task(_run_pipeline())

    # Pump messages from Socket.IO into the session queue
    await _pump_queue(session.queue, receive)


async def _pump_queue(queue: asyncio.Queue, receive) -> None:
    """Forward Socket.IO messages into the pipeline queue.
    
    On disconnect (receive returns None), stops pumping but does NOT
    put None in the queue — the pipeline stays alive for reconnects.
    """
    while True:
        msg = await receive()
        if msg is None:
            break
        if msg.get("type") in ("audio", "text"):
            await queue.put(msg)


async def _feed_queue(task: PipelineTask, queue: asyncio.Queue) -> None:
    """Read from session queue and push frames into the pipeline indefinitely."""
    await task.queue_frame(StartFrame())
    while True:
        msg = await queue.get()
        if msg is None:
            # Session explicitly ended (server-side shutdown)
            await task.queue_frame(EndFrame())
            break
        kind = msg.get("type")
        if kind == "audio":
            raw = decode_audio(msg.get("data", ""))
            if raw:
                await task.queue_frame(
                    InputAudioRawFrame(audio=raw, sample_rate=16000, num_channels=1)
                )
        elif kind == "text":
            user_text = msg.get("data", "").strip()
            if user_text:
                await task.queue_frame(
                    TranscriptionFrame(text=user_text, user_id="user", timestamp="")
                )


class TendoLLMProcessor(FrameProcessor):
    """Routes transcriptions through the Tendo LLM graph, emits TextFrame for TTS."""

    def __init__(self, session: _PipelineSession):
        super().__init__()
        self._session = session

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            text = frame.text.strip()
            if text:
                logger.info(f"Pipecat transcript → LLM: '{text[:60]}'")
                await self._session.send({"type": "thinking", "data": "Processing..."})
                result = await self._run_graph(text)
                response_text = result.get("text", "")
                if response_text:
                    await self._session.send({
                        "type": "message",
                        "data": {
                            "response": response_text,
                            "msg_type": "answer",
                            "questions": result.get("input"),
                            "extracted": result.get("extracted"),
                        },
                    })
                    await self.push_frame(TextFrame(text=response_text), direction)
            return

        await self.push_frame(frame, direction)

    async def _run_graph(self, user_text: str) -> dict:
        from app.communication.voice import _run_graph
        import asyncio
        loop = asyncio.get_event_loop()
        return await _run_graph(
            user_text=user_text,
            thread_id=self._session.session_id,
            business_id=self._session.business_id,
            send_fn=self._session.send,
            user_id=self._session.user_id,
        )


class SocketIOOutputTransport(FrameProcessor):
    """Buffers TTSAudioRawFrames and flushes on TTSStoppedFrame as one audio message."""

    def __init__(self, session: _PipelineSession, sample_rate: int = 22050):
        super().__init__()
        self._session = session
        self._sample_rate = sample_rate
        self._audio_buffer: list[bytes] = []

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TTSAudioRawFrame):
            self._audio_buffer.append(frame.audio)
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, TTSStoppedFrame):
            if self._audio_buffer:
                combined = b"".join(self._audio_buffer)
                self._audio_buffer.clear()
                await self._session.send({"type": "audio", "data": encode_audio(combined)})
                await self._session.send({"type": "turn_complete"})

        await self.push_frame(frame, direction)
