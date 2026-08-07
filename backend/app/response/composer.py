"""ResponseComposer — creates user-facing responses with streaming support."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Awaitable

from app.merge.merger import MergedResult
from app.skills.manager import SkillManager
from app.events.writer import EventStore

logger = logging.getLogger(__name__)


class ResponseComposer:
    """Creates user-facing responses with streaming support.

    Streams response immediately without waiting for background work
    (reflection, skill management, event storage).
    """

    def __init__(
        self,
        skill_manager: SkillManager | None = None,
        event_store: EventStore | None = None,
    ) -> None:
        self._skill_manager = skill_manager
        self._event_store = event_store

    async def compose(
        self,
        merged_result: MergedResult,
        streaming_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> dict:
        """Create user-facing response from MergedResult with streaming.

        Streams immediately, then dispatches background tasks concurrently.
        """
        if self._is_all_errors(merged_result):
            response = await self._stream_error_response(
                merged_result, streaming_callback
            )
        else:
            response = await self._stream_success_response(
                merged_result, streaming_callback
            )

        self._dispatch_background(merged_result)
        return response

    def _is_all_errors(self, merged_result: MergedResult) -> bool:
        has_errors = len(merged_result.errors) > 0
        has_output = bool(merged_result.combined_output)
        if has_errors and not has_output:
            return True
        if has_errors and has_output:
            non_error_values = [
                v for v in merged_result.combined_output.values()
                if isinstance(v, dict) and v.get("status") != "failure"
            ]
            return len(non_error_values) == 0
        return False

    async def _stream_success_response(
        self,
        merged_result: MergedResult,
        streaming_callback: Callable[[str], Awaitable[None]] | None,
    ) -> dict:
        response_text = self._build_response_text(merged_result)

        if streaming_callback:
            await streaming_callback(response_text)

        return {
            "response": response_text,
            "events": merged_result.events,
            "metrics": merged_result.total_metrics.model_dump(),
        }

    async def _stream_error_response(
        self,
        merged_result: MergedResult,
        streaming_callback: Callable[[str], Awaitable[None]] | None,
    ) -> dict:
        error_text = (
            "I encountered an issue processing your request. "
            "Please try again or rephrase your request."
        )

        if streaming_callback:
            await streaming_callback(error_text)

        return {
            "response": error_text,
            "events": [],
            "metrics": merged_result.total_metrics.model_dump(),
            "error": True,
        }

    @staticmethod
    def _build_response_text(merged_result: MergedResult) -> str:
        parts: list[str] = []
        output = merged_result.combined_output

        if isinstance(output, dict):
            # Try direct response field first
            response = output.get("response", "")
            if response:
                parts.append(response)
            else:
                for key, value in output.items():
                    if isinstance(value, str) and value:
                        parts.append(value)
                    elif isinstance(value, dict):
                        text = value.get("response", "")
                        if text:
                            parts.append(strip_internal_reasoning(text))

        if merged_result.errors:
            parts.append(
                "Note: Some operations encountered issues but "
                "your main request was processed."
            )

        return "\n\n".join(parts) if parts else "Done."

    def _dispatch_background(self, merged_result: MergedResult) -> None:
        """Fire-and-forget background tasks for skill management and event storage."""
        if self._skill_manager or self._event_store:
            asyncio.ensure_future(
                self._run_background(merged_result)
            )

    async def _run_background(self, merged_result: MergedResult) -> None:
        tasks: list[asyncio.Task] = []

        if self._skill_manager and merged_result.reflection_summary:
            tasks.append(
                asyncio.create_task(self._process_skills(merged_result))
            )

        if self._event_store and merged_result.events:
            tasks.append(
                asyncio.create_task(self._store_events(merged_result))
            )

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.warning("Background task failed: %s", result)

    async def _process_skills(self, merged_result: MergedResult) -> None:
        """Process skill candidates from reflection via SkillManager."""
        # Skill processing is delegated to SkillManager by the orchestrator
        # This is a placeholder hook for when reflection output is passed through
        pass

    async def _store_events(self, merged_result: MergedResult) -> None:
        """Persist business events via EventStore."""
        if not self._event_store:
            return
        for event in merged_result.events:
            try:
                self._event_store.insert_event(event)
            except Exception as e:
                logger.warning("Failed to store event: %s", e)
