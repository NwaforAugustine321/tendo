from __future__ import annotations

from abc import ABC, abstractmethod

from app.runtime.chat.message import ChatMessage

from .context import PromptContext


class PromptSection(ABC):
    """
    A PromptSection contributes one part of the final prompt.

    Examples:
        - System prompt
        - Memory
        - Few-shot examples
        - Retrieved documents (RAG)
        - Conversation history

    Sections are composed together by a PromptTemplate.
    """

    @abstractmethod
    def build(
        self,
        ctx: PromptContext,
    ) -> list[ChatMessage]:
        """
        Build this section of the prompt.

        Returns
        -------
        list[ChatMessage]
            Messages contributed by this section.
        """
        ...
