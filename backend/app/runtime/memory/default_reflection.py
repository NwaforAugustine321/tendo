from __future__ import annotations

import json

from pydantic import BaseModel, Field, ValidationError

from app.llm.client import get_client
from app.runtime.agents.run_context import RunContext

from .models import MemoryEntry
from .reflection import (
    MemoryReflection,
    MemoryReflectionEngine,
)


class ReflectionMemoryModel(BaseModel):
    text: str = Field(
        description="The durable memory.",
    )

    category: str = Field(
        default="general",
        description="Memory category.",
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        default=0.9,
        description="Confidence that this memory should be stored.",
    )


class ReflectionResponse(BaseModel):
    entries: list[ReflectionMemoryModel] = Field(
        default_factory=list,
    )


SYSTEM_PROMPT = """
You are responsible for extracting durable long-term memory from ONE completed conversation run.

You will receive only the messages generated during the latest execution.

Extract ONLY information that is likely to remain useful
in future conversations.

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
- Short-lived information
- Information already implied by previous memories

If nothing should be remembered, return:

{
  "entries": []
}

Return ONLY valid JSON matching this schema:

{
  "entries": [
    {
      "text": "User prefers Python.",
      "category": "preference",
      "confidence": 0.95
    }
  ]
}
"""


class DefaultMemoryReflection(
    MemoryReflectionEngine,
):

    def __init__(
        self,
    ) -> None:

        self._llm = get_client()

        self._structured_llm = None

        #
        # Use native structured output when supported.
        #
        if hasattr(
            self._llm,
            "with_structured_output",
        ):

            try:

                self._structured_llm = (
                    self._llm.with_structured_output(
                        ReflectionResponse,
                    )
                )

            except Exception:

                #
                # Fall back to JSON prompting.
                #
                self._structured_llm = None

    async def reflect(
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

            role = getattr(message.role, "value", str(message.role))

            # Skip tool messages — reflection only needs
            # user/assistant conversation content.
            if role == "tool":
                continue

            messages.append(
                {
                    "role": role,
                    "content": str(message.content),
                }
            )

        #
        # Native structured output.
        #
        if self._structured_llm is not None:

            result: ReflectionResponse = (
                await self._structured_llm.ainvoke(
                    messages,
                )
            )

        #
        # Generic JSON fallback.
        #
        else:

            response = await self._llm.ainvoke(
                messages,
            )

            content = getattr(
                response,
                "content",
                response,
            )

            if isinstance(
                content,
                list,
            ):
                content = "".join(
                    str(part)
                    for part in content
                )

            try:

                result = (
                    ReflectionResponse.model_validate_json(
                        str(content),
                    )
                )

            except (
                ValidationError,
                json.JSONDecodeError,
                ValueError,
            ):

                #
                # Reflection should never fail the agent.
                #
                return MemoryReflection()

        return MemoryReflection(
            entries=[
                MemoryEntry(
                    id="",
                    text=item.text,
                    category=item.category,
                    confidence=item.confidence,
                )
                for item in result.entries
            ]
        )
