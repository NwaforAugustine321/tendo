from __future__ import annotations

import asyncio

from dataclasses import dataclass

from collections.abc import Iterable
from .interface import Kind

from .interface import (
    ResponseConsumer,
    ResponseQueueInterface,
)


@dataclass(slots=True)
class ResponseItem:

    sequence: int

    text: str

    kind: str


class ResponseQueue(ResponseQueueInterface):

    def __init__(
        self,
        *,
        consumers: Iterable[ResponseConsumer] | None = None,
    ) -> None:
        self._consumers = list(
            consumers or []
        )

        self._queue: asyncio.Queue[ResponseItem] = (
            asyncio.Queue()
        )

        self._sequence = 0

        self._current: ResponseItem | None = None

        self._current_task: asyncio.Task[None] | None = None

        self._closed = False

        self._worker_task = asyncio.create_task(
            self._worker(),
        )

    async def submit(
        self,
        *,
        text: str,
        kind: str,
    ) -> None:
        if self._closed:
            return

        if not text:
            return

        self._sequence += 1

        item = ResponseItem(
            sequence=self._sequence,
            text=text,
            kind=kind,
        )

        # A real response always supersedes Presence state.
        if kind == Kind.RESPONSE:
            await self._interrupt_presence()

            self._discard_presence()

        await self._queue.put(
            item,
        )

    async def deliver(
        self,
        *,
        text: str,
        generation: int,
    ) -> None:
        """
        PresenceOutput-compatible delivery method.

        PresenceTracker does not need to know that this object
        is a ResponseQueue. It only needs the generic deliver()
        contract.
        """
        await self.submit(
            text=text,
            kind=Kind.PRESENCE_STATE,
        )

    async def _worker(
        self,
    ) -> None:
        while not self._closed:
            try:
                item = await self._queue.get()

            except asyncio.CancelledError:
                break

            if self._closed:
                self._queue.task_done()

                break

            self._current = item

            try:
                consumers = tuple(
                    self._consumers
                )

                if not consumers:
                    continue

                # Fan out the same response to every consumer.
                await asyncio.gather(
                    *(
                        self._send_to_consumer(
                            consumer,
                            item,
                        )
                        for consumer in consumers
                    ),
                    return_exceptions=True,
                )

            except asyncio.CancelledError:
                raise

            except Exception:
                pass

            finally:
                self._current = None

                self._queue.task_done()

    async def _send_to_consumer(
        self,
        consumer: ResponseConsumer,
        item: ResponseItem,
    ) -> None:
        try:
            await consumer.send(
                text=item.text,
                kind=item.kind,
                sequence=item.sequence,
            )

        except asyncio.CancelledError:
            raise

        except Exception:
            # One consumer failing must never prevent
            # the other consumers from receiving the response.
            pass

    async def _interrupt_presence(
        self,
    ) -> None:
        current = self._current

        if current is None:
            return

        if current.kind != Kind.PRESENCE_STATE:
            return

        consumers = tuple(
            self._consumers
        )

        if not consumers:
            return

        await asyncio.gather(
            *(
                self._interrupt_consumer(
                    consumer,
                )
                for consumer in consumers
            ),
            return_exceptions=True,
        )

    async def _interrupt_consumer(
        self,
        consumer: ResponseConsumer,
    ) -> None:
        try:
            await consumer.interrupt()

        except asyncio.CancelledError:
            raise

        except Exception:
            pass

    def _discard_presence(
        self,
    ) -> None:
        retained: list[ResponseItem] = []

        while True:
            try:
                item = self._queue.get_nowait()

            except asyncio.QueueEmpty:
                break

            self._queue.task_done()

            if item.kind != Kind.PRESENCE_STATE:
                retained.append(
                    item,
                )

        for item in retained:
            self._queue.put_nowait(
                item,
            )

    async def aclose(
        self,
    ) -> None:
        if self._closed:
            return

        self._closed = True

        consumers = tuple(
            self._consumers
        )

        if consumers:
            await asyncio.gather(
                *(
                    self._interrupt_consumer(
                        consumer,
                    )
                    for consumer in consumers
                ),
                return_exceptions=True,
            )

        worker = self._worker_task

        if worker is not None:
            worker.cancel()

            try:
                await worker

            except asyncio.CancelledError:
                pass

        self._worker_task = None

        self._current = None

        self._consumers.clear()

        while True:
            try:
                self._queue.get_nowait()

                self._queue.task_done()

            except asyncio.QueueEmpty:
                break
