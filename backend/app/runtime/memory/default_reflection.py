from __future__ import annotations

import logging

from app.llm.client import get_client
from app.runtime.agents.run_context import RunContext

from .models import MemoryEntry
from .reflection import (
    MemoryReflection,
    MemoryReflectionEngine,
)

logger = logging.getLogger(__name__)


EXTRACT_MEMORIES_PROMPT = """

                    You extract discrete, reusable memory statements from raw content (e.g. a task description and its result, or a conversation between a user and an assistant).

                    For the given content, output a list of memory statements. Each memory must:
                    - Be one clear sentence or short statement
                    - Be understandable without the original context
                    - Capture a decision, fact, outcome, preference, lesson, or observation worth remembering
                    - NOT be a vague summary or a restatement of the task description
                    - NOT duplicate the same idea in different words

                    When the content is a conversation, pay special attention to facts stated by the user (first-person statements). These personal facts are HIGH PRIORITY and must always be extracted:
                    - What the user did, bought, made, visited, attended, or completed
                    - Names of people, pets, places, brands, and specific items the user mentions
                    - Quantities, durations, dates, and measurements the user states
                    - Subordinate clauses and casual asides often contain important personal details (e.g. "by the way, it took me 4 hours" or "my Golden Retriever Max")

                    Also extract from assistant and tool messages:
                    - Facts the assistant discovered or confirmed via tools
                    - Results of searches, lookups, or calculations that reveal user context
                    - Decisions or recommendations the user accepted

                    Preserve exact names and numbers — never generalize (e.g. keep "lavender gin fizz" not just "cocktail", keep "12 largemouth bass" not just "fish caught", keep "Golden Retriever" not just "dog").

                    Additional extraction rules:
                    - Presupposed facts: When the user reveals a fact indirectly in a question (e.g. "What collar suits a Golden Retriever like Max?" presupposes Max is a Golden Retriever), extract that fact as a separate memory.
                    - Date precision: Always preserve the full date including day-of-month when stated (e.g. "February 14th" not just "February", "March 5" not just "March").
                    - Life events in passing: When the user mentions a life event (birth, wedding, graduation, move, adoption) while discussing something else, extract the life event as its own memory (e.g. "my friend David had a baby boy named Jasper" is a birth fact, even if mentioned while planning to send congratulations).

                    If there is nothing worth remembering (e.g. empty result, no decisions or facts), return exactly: NONE

                    Otherwise return one memory per line as plain text. No JSON. No formatting. No bullets. No numbering.
                    """


class DefaultMemoryReflection(
    MemoryReflectionEngine,
):

    def __init__(self) -> None:
        self._llm = get_client()

    async def reflect(
        self,
        ctx: RunContext,
    ) -> MemoryReflection:

        try:
            return await self._do_reflect(ctx)
        except Exception:
            logger.debug(
                "Memory reflection skipped.",
                exc_info=True,
            )
            return MemoryReflection()

    async def _do_reflect(
        self,
        ctx: RunContext,
    ) -> MemoryReflection:

        if not ctx.messages:
            return MemoryReflection()

        # Build conversation content including all roles
        # (user, assistant, tool, system).
        conversation_lines = []

        for message in ctx.messages:

            if not message.content:
                continue

            role = getattr(
                message.role, "value", str(message.role)
            )

            # Skip system messages — they're instructions,
            # not conversation content.
            if role == "system":
                continue

            content = message.content
            if not isinstance(content, str):
                content = str(content)

            conversation_lines.append(
                f"{role}: {content.strip()}"
            )

        if not conversation_lines:
            return MemoryReflection()

        conversation_text = "\n".join(conversation_lines)

        messages = [
            {
                "role": "system",
                "content": EXTRACT_MEMORIES_PROMPT,
            },
            {
                "role": "user",
                "content": conversation_text,
            },
        ]

        response = await self._llm.ainvoke(messages)

        content = getattr(response, "content", response)

        if isinstance(content, list):
            content = "".join(str(part) for part in content)

        content = str(content).strip()

        if not content or content.upper() == "NONE":
            return MemoryReflection()

        # Each line is one memory.
        memories = [
            line.strip()
            for line in content.splitlines()
            if line.strip()
            and line.strip().upper() != "NONE"
        ]

        if not memories:
            return MemoryReflection()

        entries = [
            MemoryEntry(
                id="",
                text=str(item).strip(),
                category="general",
            )
            for item in memories
            if item and str(item).strip()
        ]

        return MemoryReflection(entries=entries)
