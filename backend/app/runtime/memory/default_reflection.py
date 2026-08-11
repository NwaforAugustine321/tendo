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


SYSTEM_PROMPT = """
You are responsible for extracting durable long-term memory from ONE completed conversation run.

Extract ONLY information that is likely to remain useful in future conversations.

Store:
- User preferences
- Long-term goals
- Ongoing projects
- Stable personal facts
- Stable business facts

Do NOT store:
- Greetings
- Temporary requests
- Tool outputs
- Small talk
- One-time questions

If nothing should be remembered, return exactly: NONE

Otherwise return one memory per line as plain text. No JSON. No formatting.

Example:
User prefers Python
User is building a SaaS for restaurants
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

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

        for message in ctx.messages:

            if not message.content:
                continue

            role = getattr(
                message.role, "value", str(message.role)
            )

            if role == "tool":
                continue

            messages.append(
                {
                    "role": role,
                    "content": str(message.content),
                }
            )

        response = await self._llm.ainvoke(messages)

        content = getattr(response, "content", response)

        if isinstance(content, list):
            content = "".join(str(part) for part in content)

        content = str(content).strip()

        if not content or content.upper() == "NONE":
            return MemoryReflection()

        # Each line is one memory.
        lines = [
            line.strip()
            for line in content.splitlines()
            if line.strip() and line.strip().upper() != "NONE"
        ]

        if not lines:
            return MemoryReflection()

        entries = [
            MemoryEntry(
                id="",
                text=line,
                category="general",
            )
            for line in lines
        ]

        return MemoryReflection(entries=entries)
