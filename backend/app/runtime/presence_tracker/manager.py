from __future__ import annotations

import asyncio
from time import monotonic

from .config import PresenceTrackerConfig
from .interface import (
    PresenceLLM,
    PresenceOutput,
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

        self._started = False
        self._closed = False

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

        self._last_response_at = (
            now
            - self._config.minimum_response_interval
        )

        self._last_user_activity_at = now
        self._last_state_event_at = now

        self._started = True
        self._interrupt_event.clear()

        self._state = PresenceState(
            user_request=user_request,
            max_response_length=(
                self._config.max_response_length
            ),
        )

        # Fire immediately without blocking the main runner.
        self._trigger_generation(
            force=True,
        )

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

        # Invalidate any generation currently working.
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
        ):
            return

        if state is not None:
            # Status changes update the current runtime state, but they do
            # not create a new Presence run. Preserve the original runtime
            # clock so elapsed time continues from start().
            started_at = self._state.started_at

            self._state = state.snapshot()
            self._state.started_at = started_at
            self._state.elapsed_seconds = self._state.elapsed

        self._last_state_event_at = monotonic()

        # A state event changes the context available to the next presence
        # generation. It must NOT reset the pacing signals:
        #
        #   - elapsed runtime
        #   - response backoff / minimum response interval
        #   - interval progression (40s -> 60s -> 90s -> 120s -> ...)
        #
        # Do not invalidate an already-running generation here. In a voice
        # agent, frequent runtime status events are normal and forcing a new
        # generation for each one would cause overlapping/repeated speech.
        #
        # The next generation will take a snapshot of the latest state when
        # the existing pacing rules allow it.
        self._evaluate_presence()

    def stop(self) -> None:
        if not self._started:
            return

        self._started = False

        # Invalidate every outstanding generation.
        self._generation += 1

        self._interval_index = 0

        # Signal consumers that current presence output
        # should be interrupted/stopped.
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

        # Invalidate all outstanding work.
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
            or self._state is None
        ):
            return

        # Never start another generation while one is running.
        if (
            self._generation_task is not None
            and not self._generation_task.done()
        ):
            return

        if not self._interval_elapsed():
            self._schedule_timer()
            return

        if not self._silence_elapsed():
            self._schedule_timer()
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
                or self._state is None
            ):
                return

            self._timer_task = None

            self._evaluate_presence()

        except asyncio.CancelledError:
            raise

    def _trigger_generation(
        self,
        *,
        force: bool = False,
    ) -> None:
        if (
            self._closed
            or not self._started
            or self._state is None
        ):
            return

        if (
            self._generation_task is not None
            and not self._generation_task.done()
        ):
            return

        if not force:
            if not self._interval_elapsed():
                self._schedule_timer()
                return

            if not self._silence_elapsed():
                self._schedule_timer()
                return

        now = monotonic()

        if (
            not force
            and (
                now - self._last_response_at
                < self._config.minimum_response_interval
            )
        ):
            self._schedule_timer()
            return

        generation = self._generation

        state = self._state.snapshot()
        state.elapsed_seconds = state.elapsed

        self._generation_task = asyncio.create_task(
            self._generate(
                state=state,
                generation=generation,
            ),
        )

    async def _generate(
        self,
        *,
        state: PresenceState,
        generation: int,
    ) -> None:
        try:

            text = await self._llm.generate(
                state=state,
            )

            if not text:
                if self._is_generation_valid(
                    generation,
                ):
                    self._schedule_timer()

                return

            if not self._is_generation_valid(
                generation,
            ):
                return

            text = text.strip()

            if not text:
                if self._is_generation_valid(
                    generation,
                ):
                    self._schedule_timer()

                return

            max_length = (
                state.max_response_length
                or self._config.max_response_length
            )

            if len(text) > max_length:
                text = text[
                    :max_length
                ].rstrip()

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
