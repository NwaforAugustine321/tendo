from __future__ import annotations

from app.runtime.chat.message import ChatMessage

from ..context import PromptContext
from ..section import PromptSection
import logging

logger = logging.getLogger(__name__)


class SystemSection(PromptSection):
    """
    Contributes the Agent's system instructions.

    This is typically the first message in the prompt.
    """

    def build(
        self,
        ctx: PromptContext
    ) -> list[ChatMessage]:

        instructions = ctx.agent.instructions.strip()

        if not instructions:
            return []

        return [
            ChatMessage(
                role="system",
                content=instructions,
            )
        ]
