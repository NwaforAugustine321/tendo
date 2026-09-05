
from __future__ import annotations

import asyncio

from time import monotonic

from .config import PresenceTrackerConfig

from .interface import (
    PresenceAction,
    PresenceLLM,
    PresenceOutput,
    PresencePhase,
    PresenceResult,
)

from .state import PresenceState


class PresenceTracker:

    def __init__(
        self,
        *,
        llm: PresenceLLM,
        output: PresenceOutput,
        config: PresenceTrackerConfig | None = None,
    ) -> None:
        self._llm = llm

        self._output = output

        self._config = (
            config
            if config is not None
            else PresenceTrackerConfig()
        )

        self._state: PresenceState | None = None

        self._timer_task: asyncio.Task[None] | None = None

        self._generation_task: asyncio.Task[None] | None = None

        self._generation = 0

        self._interval_index = 0

        self._last_response_at = 0.0

        self._last_user_activity_at = 0.0

        self._last_state_event_at = 0.0

        self._last_delivered_state: tuple[str, str] | None = None

        self._last_delivered_text = ""

        self._started = False

        self._closed = False

        self._progress_enabled = False

        self._interrupt_event = asyncio.Event()

    @property
    def state(self) -> PresenceState | None:

        if self._state is None:
            return None

        state = self._state.snapshot()

        state.elapsed_seconds = state.elapsed

        return state

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def interrupted(self) -> bool:
        return self._interrupt_event.is_set()

    @property
    def interrupt_event(self) -> asyncio.Event:
        return self._interrupt_event

    @property
    def elapsed_seconds(self) -> float:

        if self._state is None:
            return 0.0

        return self._state.elapsed

    @property
    def silence_seconds(self) -> float:

        if not self._started:
            return 0.0

        return max(
            0.0,
            monotonic() - self._last_user_activity_at,
        )

    @property
    def response_elapsed_seconds(self) -> float:

        if not self._started:
            return 0.0

        return max(
            0.0,
            monotonic() - self._last_response_at,
        )

    @property
    def next_presence_in_seconds(self) -> float:

        if (
            not self._started
            or self._state is None
        ):
            return 0.0

        return self._presence_delay()

    def start(
        self,
        *,
        user_request: str,
    ) -> None:

        if self._closed or not self._config.enabled:
            return

        self.stop()

        now = monotonic()

        self._generation += 1

        self._interval_index = 0

        self._last_delivered_state = None

        self._last_delivered_text = ""

        self._last_response_at = (
            now
            - self._config.minimum_response_interval
        )

        self._last_user_activity_at = now

        self._last_state_event_at = now

        self._started = True

        self._progress_enabled = False

        self._interrupt_event.clear()

        self._state = PresenceState(
            user_request=user_request,
            max_response_length=(
                self._config.max_response_length
            ),
        )

    async def classify(
        self,
        *,
        user_request: str | None = None,
    ) -> PresenceResult:

        if (
            self._closed
            or not self._config.enabled
            or not self._started
            or self._state is None
        ):
            return PresenceResult(
                action=PresenceAction.HANDOFF,
            )

        if user_request is not None:
            self._prepare_new_request(
                user_request,
            )

        generation = self._generation

        if not self._is_generation_valid(
            generation,
        ):
            return PresenceResult(
                action=PresenceAction.HANDOFF,
            )

        state = self._state.snapshot()

        state.elapsed_seconds = state.elapsed

        try:

            result = await self._llm.generate(
                state=state,
                phase=PresencePhase.INITIAL,
            )

        except asyncio.CancelledError:
            raise

        except Exception:

            if self._is_generation_valid(
                generation,
            ):
                self._progress_enabled = True

                self._schedule_timer()

            return PresenceResult(
                action=PresenceAction.HANDOFF,
            )

        if not self._is_generation_valid(
            generation,
        ):
            return PresenceResult(
                action=PresenceAction.HANDOFF,
            )

        max_length = (
            state.max_response_length
            or self._config.max_response_length
        )

        message = (
            result.message.strip()
            if result.message
            else None
        )

        if message and len(message) > max_length:

            message = message[
                :max_length
            ].rstrip()

        if result.action == PresenceAction.RESPOND:

            if not message:

                self._progress_enabled = True

                self._schedule_timer()

                return PresenceResult(
                    action=PresenceAction.HANDOFF,
                )

            await self._deliver_initial_message(
                text=message,
                generation=generation,
            )

            return PresenceResult(
                action=PresenceAction.RESPOND,
                message=message,
            )

        if result.action == PresenceAction.HANDOFF:

            if message:

                await self._deliver_initial_message(
                    text=message,
                    generation=generation,
                )

            if self._is_generation_valid(
                generation,
            ):
                self._progress_enabled = True

                self._schedule_timer()

            return PresenceResult(
                action=PresenceAction.HANDOFF,
                message=message,
            )

        if message:

            await self._deliver_initial_message(
                text=message,
                generation=generation,
            )

        if self._is_generation_valid(
            generation,
        ):
            self._progress_enabled = True

            self._schedule_timer()

        return PresenceResult(
            action=PresenceAction.HANDOFF,
            message=message,
        )

    async def _deliver_initial_message(
        self,
        *,
        text: str,
        generation: int,
    ) -> None:

        if not self._is_generation_valid(
            generation,
        ):
            return

        await self._output.deliver(
            text=text,
            generation=generation,
        )

        if not self._is_generation_valid(
            generation,
        ):
            return

        self._last_response_at = monotonic()

        self._last_delivered_text = text

    def _prepare_new_request(
        self,
        user_request: str,
    ) -> None:

        if self._state is None:
            return

        self._generation += 1

        self._progress_enabled = False

        self._cancel_task(
            self._timer_task,
        )

        self._timer_task = None

        self._cancel_task(
            self._generation_task,
        )

        self._generation_task = None

        self._interval_index = 0

        self._last_delivered_state = None

        self._last_delivered_text = ""

        self._last_response_at = (
            monotonic()
            - self._config.minimum_response_interval
        )

        self._last_user_activity_at = monotonic()

        self._last_state_event_at = (
            self._last_user_activity_at
        )

        state = self._state.snapshot()

        state.user_request = user_request

        state.elapsed_seconds = state.elapsed

        self._state = state

        self._interrupt_event.clear()

    def update(
        self,
        *,
        state: PresenceState,
    ) -> None:

        if (
            self._closed
            or not self._started
            or self._state is None
        ):
            return

        self._state = state.snapshot()

        self._state.elapsed_seconds = (
            self._state.elapsed
        )

        self._last_state_event_at = monotonic()

        self._evaluate_presence()

    def notify_user_activity(self) -> None:

        if (
            self._closed
            or not self._started
        ):
            return

        self._last_user_activity_at = monotonic()

        self._generation += 1

        self._cancel_task(
            self._generation_task,
        )

        self._generation_task = None

        self._cancel_task(
            self._timer_task,
        )

        self._timer_task = None

        self._schedule_timer()

    def notify_state_event(
        self,
        *,
        state: PresenceState | None = None,
    ) -> None:

        if (
            self._closed
            or not self._started
            or self._state is None
            or not self._progress_enabled
        ):
            return

        if state is not None:

            started_at = self._state.started_at

            self._state = state.snapshot()

            self._state.started_at = started_at

            self._state.elapsed_seconds = (
                self._state.elapsed
            )

        self._last_state_event_at = monotonic()

        self._evaluate_presence()

    def stop(self) -> None:

        if not self._started:
            return

        self._started = False

        self._progress_enabled = False

        self._generation += 1

        self._interval_index = 0

        self._interrupt_event.set()

        self._cancel_task(
            self._timer_task,
        )

        self._timer_task = None

        self._cancel_task(
            self._generation_task,
        )

        self._generation_task = None

    async def aclose(self) -> None:

        if self._closed:
            return

        self._closed = True

        self._started = False

        self._progress_enabled = False

        self._generation += 1

        self._interrupt_event.set()

        await self._cancel_and_wait(
            self._timer_task,
        )

        await self._cancel_and_wait(
            self._generation_task,
        )

        self._timer_task = None

        self._generation_task = None

    def _evaluate_presence(self) -> None:

        if (
            self._closed
            or not self._started
            or not self._progress_enabled
            or self._state is None
        ):
            return

        if (
            self._generation_task is not None
            and not self._generation_task.done()
        ):
            return

        self._trigger_generation()

    def _interval_elapsed(self) -> bool:

        return (
            self.response_elapsed_seconds
            >= self._current_interval()
        )

    def _silence_elapsed(self) -> bool:

        return (
            self.silence_seconds
            >= self._config.silence_threshold
        )

    def _presence_delay(self) -> float:

        interval_remaining = max(
            0.0,
            self._current_interval()
            - self.response_elapsed_seconds,
        )

        silence_remaining = max(
            0.0,
            self._config.silence_threshold
            - self.silence_seconds,
        )

        return max(
            interval_remaining,
            silence_remaining,
        )

    def _schedule_timer(self) -> None:

        if (
            self._closed
            or not self._started
            or not self._progress_enabled
            or self._state is None
            or not self._config.intervals
        ):
            return

        if self._timer_task is not None:

            if not self._timer_task.done():
                return

        delay = self._presence_delay()

        self._timer_task = asyncio.create_task(
            self._wait_and_evaluate(
                delay,
            ),
        )

    async def _wait_and_evaluate(
        self,
        delay: float,
    ) -> None:

        try:

            if delay:
                await asyncio.sleep(delay)

            if (
                self._closed
                or not self._started
                or not self._progress_enabled
                or self._state is None
            ):
                return

            self._timer_task = None

            self._evaluate_presence()

        except asyncio.CancelledError:
            raise

    def _trigger_generation(self) -> None:

        if (
            self._closed
            or not self._started
            or not self._progress_enabled
            or self._state is None
        ):
            return

        if (
            self._generation_task is not None
            and not self._generation_task.done()
        ):
            return

        # Every PROGRESS generation is gated.

        if not self._interval_elapsed():

            self._schedule_timer()

            return

        if not self._silence_elapsed():

            self._schedule_timer()

            return

        now = monotonic()

        if (
            now - self._last_response_at
            < self._config.minimum_response_interval
        ):

            self._schedule_timer()

            return

        generation = self._generation

        state = self._state.snapshot()

        state.elapsed_seconds = state.elapsed

        state_key = (
            state.status,
            state.stage,
        )

        self._generation_task = asyncio.create_task(
            self._generate(
                state=state,
                state_key=state_key,
                generation=generation,
            ),
        )

    async def _generate(
        self,
        *,
        state: PresenceState,
        state_key: tuple[str, str],
        generation: int,
    ) -> None:

        try:

            result = await self._llm.generate(
                state=state,
                phase=PresencePhase.PROGRESS,
            )

            if not self._is_generation_valid(
                generation,
            ):
                return

            if result.action != PresenceAction.STATUS:

                self._schedule_timer()

                return

            text = (
                result.message.strip()
                if result.message
                else None
            )

            if not text:

                self._schedule_timer()

                return

            if not self._is_generation_valid(
                generation,
            ):
                return

            current_state = self._state

            if current_state is None:
                return

            current_state_key = (
                current_state.status,
                current_state.stage,
            )

            # The state may have changed while the LLM was
            # generating. Never deliver a stale response.

            if current_state_key != state_key:

                self._schedule_timer()

                return

            await self._output.deliver(
                text=text,
                generation=generation,
            )

            if not self._is_generation_valid(
                generation,
            ):
                return

            self._last_response_at = monotonic()

            self._last_delivered_state = state_key

            self._last_delivered_text = text

            if (
                self._interval_index
                < len(self._config.intervals) - 1
            ):

                self._interval_index += 1

            else:

                self._interval_index = 0

            self._schedule_timer()

        except asyncio.CancelledError:
            raise

        except Exception:

            if self._is_generation_valid(
                generation,
            ):
                self._schedule_timer()

    def _is_generation_valid(
        self,
        generation: int,
    ) -> bool:

        return (
            not self._closed
            and self._started
            and generation == self._generation
        )

    def _current_interval(self) -> float:

        return self._config.intervals[
            min(
                self._interval_index,
                len(self._config.intervals) - 1,
            )
        ]

    @staticmethod
    def _cancel_task(
        task: asyncio.Task[None] | None,
    ) -> None:

        if task is not None and not task.done():
            task.cancel()

    @staticmethod
    async def _cancel_and_wait(
        task: asyncio.Task[None] | None,
    ) -> None:

        if task is None or task.done():
            return

        task.cancel()

        try:
            await task

        except asyncio.CancelledError:
            pass
