from __future__ import annotations

from app.runtime.chat.message import ChatMessage

from .context import PromptContext


class PromptBuilder:
    """
    Builds the final prompt for an inference.
    """

    def __init__(
        self,
        *,
        context: PromptContext,
    ) -> None:

        self._context = context

    @property
    def context(
        self,
    ) -> PromptContext:
        return self._context

    def build(
        self,
    ) -> list[ChatMessage]:
        """
        Build the complete prompt.

        Returns
        -------
        list[ChatMessage]
            chat messages.
        """

        return self._context.agent.prompt_template.build(
            self._context,
        )
