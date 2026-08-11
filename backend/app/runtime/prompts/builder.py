from __future__ import annotations

from app.runtime.chat.message import ChatMessage
from app.runtime.memory.builder import MemoryPromptBuilder
from app.runtime.structured_output.formatter import OutputFormatter
from app.runtime.prompts.sections.conversation import (
    ConversationPromptBuilder,
)
from app.runtime.prompts.sections.user_task import (
    UserTaskPromptBuilder,
)
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

        self._task_builder = UserTaskPromptBuilder()
        self._conversation_builder = ConversationPromptBuilder()
        self._memory_builder = MemoryPromptBuilder()
        self._rag_builder = RAGPromptBuilder()
        self._output_formatter = OutputFormatter()

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

        #
        # User task
        #
        prompt = self._task_builder.build(
            self._context.run_context,
        )

        if prompt:
            parts.append(
                prompt,
            )

        #
        # Conversation history
        #
        prompt = self._conversation_builder.build(
            self._context.conversation_context,
        )

        if prompt:
            parts.append(
                prompt,
            )

        #
        # Memory
        #
        prompt = await self._build_memory_prompt()

        if prompt:
            parts.append(
                prompt,
            )

        #
        # Retrieved knowledge
        #
        prompt = await self._build_rag_prompt()

        if prompt:
            parts.append(
                prompt,
            )

        #
        # Agent instructions
        #
        template_messages = self._context.agent.prompt_template.build(
            self._context,
        )

        #
        # Structured output
        #
        prompt = self._output_formatter.build(
            self._context.agent.output_type,
        )

        if prompt:
            parts.append(
                prompt,
            )

        messages: list[ChatMessage] = []

        if parts:

            messages.append(
                ChatMessage.system(
                    "\n\n".join(parts),
                )
            )

        #
        # Template-contributed messages.
        #
        if template_messages:
            messages.extend(
                template_messages,
            )

        #
        # Current inference messages.
        #
        messages.extend(
            self._context.run_context.messages,
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
