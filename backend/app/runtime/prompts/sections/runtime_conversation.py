from __future__ import annotations

from app.runtime.chat.message import ChatMessage

from ..context import PromptContext
from ..section import PromptSection


class RunTimeConversationSection(PromptSection):
    """
    Contributes the loaded conversation history.
    """

    def build(
        self,
        ctx: PromptContext,
    ) -> list[ChatMessage]:

        return list(
            ctx.conversation_context.messages,
        )
