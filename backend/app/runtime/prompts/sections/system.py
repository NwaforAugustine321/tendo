from __future__ import annotations

from app.runtime.chat.message import ChatMessage

from ..context import PromptContext
from ..section import PromptSection
import logging

logger = logging.getLogger(__name__)


class SystemSection(PromptSection):
    """
    Contributes the Agent's system instructions.
    """

    HEADER = (
        "[IMMUTABLE DISCLOSURE POLICIES]\n"
        "{action_response_protocol}"
        "{privacy_policies}"
        "[IMMUTABLE DISCLOSURE POLICIES]\n\n"
        "[IMMUTABLE DISCLOSURE POLICIES SYSTEM INSTRUCTIONS]\n"
        "{instructions}\n"
        "{parts}\n"
        "[IMMUTABLE DISCLOSURE POLICIES SYSTEM INSTRUCTIONS]\n\n"
    )

    def build(
        self,
        ctx: PromptContext,
        system_parts_instr: str
    ) -> list[ChatMessage]:

        instructions = ctx.agent.instructions.strip()

        if not instructions:
            return []

        instructions = instructions.replace("{action_response_protocol}", (
            "\n"
            f"{ctx.run_context.i18n.get('reasoning.action_reasoning')}"
            "\n\n"
        ))

        instructions = instructions.replace("{privacy_policies}", (
            "[IMMUTABLE DISCLOSURE POLICIES]\n"
            f"{ctx.run_context.i18n.get('slices.governance_policy')}"
            "[IMMUTABLE DISCLOSURE POLICIES]\n\n"
        ))

        instructions = self.HEADER.replace('{instructions}', str(instructions))\
            .replace('{parts}', str(system_parts_instr))

        return [
            ChatMessage(
                role="system",
                content=instructions,
            )
        ]
