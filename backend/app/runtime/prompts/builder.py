from __future__ import annotations

from app.runtime.chat.message import ChatMessage
from app.runtime.memory.builder import MemoryPromptBuilder
from app.runtime.rag.builder import RAGPromptBuilder

from .context import PromptContext


class PromptBuilder:
    """
    Builds the complete prompt for an inference.
    """

    def __init__(
        self,
        *,
        context: PromptContext,
    ) -> None:

        self._context = context

        self._memory_builder = MemoryPromptBuilder()
        self._rag_builder = RAGPromptBuilder()

    @property
    def context(
        self,
    ) -> PromptContext:

        return self._context

    async def build(
        self,
    ) -> list[ChatMessage]:
        """
        Build the complete prompt.

        Returns
        -------
        list[ChatMessage]
            Messages sent to the LLM.
        """

        parts: list[str] = []

        memory_prompt = await self._build_memory_prompt()

        if memory_prompt:
            parts.append(
                memory_prompt,
            )

        rag_prompt = await self._build_rag_prompt()

        if rag_prompt:
            parts.append(
                rag_prompt,
            )

        agent_prompt = self._context.agent.prompt_template.build(
            self._context,
        )

        if agent_prompt:
            parts.append(
                agent_prompt,
            )

        messages: list[ChatMessage] = []

        if parts:

            messages.append(
                ChatMessage.system(
                    "\n\n".join(parts),
                )
            )

        messages.extend(
            self._context.chat_context.messages,
        )

        return messages

    async def _build_memory_prompt(
        self,
    ) -> str:

        agent = self._context.agent

        if agent.memory is None:
            return ""

        memory = await agent.memory.retrieve(
            self._context.run_context,
        )

        return self._memory_builder.build(
            memory,
        )

    async def _build_rag_prompt(
        self,
    ) -> str:

        agent = self._context.agent

        if agent.rag is None:
            return ""

        knowledge = await agent.rag.retrieve(
            self._context.run_context,
        )

        return self._rag_builder.build(
            knowledge,
        )
