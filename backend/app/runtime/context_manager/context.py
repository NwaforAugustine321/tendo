from __future__ import annotations

from dataclasses import dataclass

from app.runtime.chat.message import ChatMessage
from app.runtime.prompts.builder import PromptBuilder


@dataclass(slots=True)
class ContextManagerContext:
    """
    Context used by ContextManager.
    """

    builder: PromptBuilder

    messages: list[ChatMessage]
