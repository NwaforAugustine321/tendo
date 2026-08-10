from __future__ import annotations

from app.runtime.chat.message import ChatMessage

from ..context import PromptContext
from ..section import PromptSection


class ConversationSection(PromptSection):
    """
    Contributes the current conversation history.
    """

    def build(
        self,
        ctx: PromptContext,
    ) -> list[ChatMessage]:

        return list(
            ctx.chat_context.messages,
        )
