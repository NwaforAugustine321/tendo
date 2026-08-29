from __future__ import annotations

import json

from app.runtime.chat.message import ChatMessage

from ..context import PromptContext
from ..section import PromptSection
from app.runtime.structured_output.formatter import (
    OutputFormatter,
)


class OutputSection(PromptSection):

    def build(
        self,
        ctx: PromptContext,
    ) -> list[ChatMessage]:

        output_type = ctx.agent.output_type

        if output_type is None:
            return []

        if ctx.agent.llm.supports_structured_output:
            return []

        formatter = OutputFormatter()

        return [
            ChatMessage.system(
                formatter.build_prompt(
                    output_type,
                )
            )
        ]
