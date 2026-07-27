"""ThinkingStreamCallback — streams thinking/thought tokens during agent execution."""

from __future__ import annotations

import re
from typing import Any
from collections.abc import Callable

from langchain_core.callbacks import AsyncCallbackHandler


class ThinkingStreamCallback(AsyncCallbackHandler):
    """Streams thinking/thought to client via thinking_callback during agent execution."""

    def __init__(self, thinking_callback: Callable | None = None):
        super().__init__()
        self.thinking_callback = thinking_callback
        self._buffer = ""
        self._last_emitted_len = 0

    def reset(self) -> None:
        self._buffer = ""
        self._last_emitted_len = 0

    async def _send(self, msg: dict) -> None:
        if not self.thinking_callback:
            return
        try:
            await self.thinking_callback(msg)
        except Exception:
            pass

    async def on_llm_new_token(self, token: str, *, chunk=None, **kwargs: Any) -> None:
        if not token and not chunk:
            return

        if chunk and hasattr(chunk, "additional_kwargs") and "reasoning_content" in chunk.additional_kwargs:
            reasoning = chunk.message.additional_kwargs.get("reasoning_content")
            if reasoning:
                await self._send({"type": "thought", "data": reasoning})
                return

        if not token:
            return

        self._buffer += token

        if "<Thought>" in self._buffer:
            after = self._buffer.split("<Thought>", 1)[1]
            thought_text = after.split("</Thought>", 1)[0].strip()
            thought_text = re.sub(r"</T(?:h(?:o(?:u(?:g(?:h(?:t)?)?)?)?)?)?\s*$", "", thought_text).strip()
            if thought_text and len(thought_text) > self._last_emitted_len + 30:
                self._last_emitted_len = len(thought_text)
                await self._send({"type": "thought", "data": thought_text})

    async def on_llm_start(self, serialized: dict | None = None, prompts: list | None = None, **kwargs: Any) -> None:
        self.reset()

    async def on_chat_model_start(self, serialized: dict | None = None, messages: list | None = None, **kwargs: Any) -> None:
        self.reset()
        await self._send({"type": "thinking", "data": "Thinking..."})

    async def on_llm_end(self, response: Any = None, **kwargs: Any) -> None:
        pass
