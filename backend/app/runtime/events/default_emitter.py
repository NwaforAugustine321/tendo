from __future__ import annotations

import inspect
from typing import Any

from .emitter import (
    Callback,
    Emitter,
)


class DefaultEmitter(
    Emitter,
):
    """
    Default in-process event emitter.

    Supports:
    - Multiple callbacks per event.
    - Synchronous callbacks.
    - Asynchronous callbacks.
    - Event-specific subscriptions.
    - Duplicate callback protection.
    """

    def __init__(self) -> None:

        self._callbacks: dict[
            str,
            list[Callback],
        ] = {}

    @staticmethod
    def _event_key(
        event: str,
    ) -> str:
        """
        Normalize an event into a string key.

        Supports both plain string events and
        Enum-based events such as EventType.STATUS.
        """

        return (
            event.value
            if hasattr(event, "value")
            else event
        )

    def on(
        self,
        event: str,
        callbacks: list[Callback],
    ) -> None:
        """
        Register callbacks for a specific event.

        The same callback will only be registered
        once for the same event.
        """

        if not callbacks:
            return

        event_key = self._event_key(
            event,
        )

        registered = self._callbacks.setdefault(
            event_key,
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

        Missing callbacks are ignored.
        """

        if not callbacks:
            return

        event_key = self._event_key(
            event,
        )

        registered = self._callbacks.get(
            event_key,
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
                event_key,
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

        event_key = self._event_key(
            event,
        )

        callbacks = self._callbacks.get(
            event_key,
        )

        if not callbacks:
            return

        #
        # Use a snapshot so callbacks can safely
        # register or unregister callbacks while
        # an event is being emitted.
        #
        for callback in tuple(callbacks):

            result = callback(
                payload,
            )

            if inspect.isawaitable(
                result,
            ):
                await result
