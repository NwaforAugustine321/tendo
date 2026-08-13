from __future__ import annotations

from typing import Any

from .emitter import (
    Callback,
    Emitter,
)


class DefaultEmitter(
    Emitter,
):
    """
    Default  event emitter.
    """

    def __init__(self) -> None:

        self._callbacks: dict[
            str,
            list[Callback],
        ] = {}

    def on(
        self,
        event: str,
        callbacks: list[Callback],
    ) -> None:
        """
        Register callbacks for a specific event.

        """

        if not callbacks:
            return

        registered = self._callbacks.setdefault(
            event,
            [],
        )

        for callback in callbacks:

            if callback not in registered:
                registered.append(
                    callback,
                )

    def off(
        self,
        event: str,
        callbacks: list[Callback],
    ) -> None:
        """
        Remove callbacks from a specific event.
        """

        registered = self._callbacks.get(
            event,
        )

        if not registered:
            return

        for callback in callbacks:

            try:
                registered.remove(
                    callback,
                )
            except ValueError:
                continue

        if not registered:
            self._callbacks.pop(
                event,
                None,
            )

    async def emit(
        self,
        event: str,
        payload: Any = None,
    ) -> None:
        """
        Emit an event only to callbacks registered
        for that specific event.
        """

        callbacks = self._callbacks.get(
            event,
        )

        if not callbacks:
            return

        for callback in tuple(callbacks):

            result = callback(
                payload,
            )

            if result is not None:
                await result
