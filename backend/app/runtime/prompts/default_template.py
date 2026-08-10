from __future__ import annotations

from app.runtime.prompts.template import PromptTemplate
from app.runtime.prompts.sections.system import SystemSection
from app.runtime.prompts.sections.runtime_conversation import RunTimeConversationSection


class DefaultPromptTemplate(
    PromptTemplate,
):

    def __init__(self):

        super().__init__(
            [
                SystemSection(),
                RunTimeConversationSection(),
            ]
        )
