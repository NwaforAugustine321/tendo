from __future__ import annotations

from collections.abc import Iterable

from app.runtime.chat.message import ChatMessage

from .context import PromptContext
from .section import PromptSection


class PromptTemplate:
    """
    A PromptTemplate defines the order in which
    PromptSections contribute to the final prompt.
    """

    def __init__(
        self,
        sections: Iterable[PromptSection],
    ) -> None:

        self._sections = list(
            sections,
        )

    @property
    def sections(
        self,
    ) -> list[PromptSection]:
        return self._sections

    def add(
        self,
        section: PromptSection,
    ) -> None:

        self._sections.append(
            section,
        )

    def extend(
        self,
        sections: Iterable[PromptSection],
    ) -> None:

        self._sections.extend(
            sections,
        )

    def build(
        self,
        ctx: PromptContext,
    ) -> list[ChatMessage]:
        """
        Build the complete prompt by asking each
        PromptSection to contribute messages.
        """

        messages: list[ChatMessage] = []

        for section in self._sections:

            messages.extend(
                section.build(
                    ctx,
                )
            )

        return messages
