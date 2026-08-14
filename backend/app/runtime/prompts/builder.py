from __future__ import annotations

import logging

from langchain_core.messages.utils import (
    count_tokens_approximately,
)

from app.runtime.chat.message import ChatMessage
from app.runtime.memory.builder import MemoryPromptBuilder
from app.runtime.prompts.sections.conversation import (
    ConversationPromptBuilder,
)
from app.runtime.prompts.sections.user_task import (
    UserTaskPromptBuilder,
)
from app.runtime.rag.builder import RAGPromptBuilder
from app.runtime.structured_output.formatter import OutputFormatter

from .context import PromptContext


logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Builds the prompt for an AgentSession.

    Prompt construction is divided into two parts:

    Stable
    ------
    Built once and stored in PromptState.

    Dynamic
    -------
    Current execution messages are appended at inference
    time.

    The stable prompt is rebuilt only when PromptState is
    invalidated, for example after conversation optimization.
    """

    def __init__(
        self,
        *,
        context: PromptContext,
    ) -> None:

        self._context = context

        self._conversation_builder = (
            ConversationPromptBuilder()
        )

        self._memory_builder = (
            MemoryPromptBuilder()
        )

        self._rag_builder = (
            RAGPromptBuilder()
        )

        self._output_formatter = (
            OutputFormatter()
        )

    @property
    def context(
        self,
    ) -> PromptContext:

        return self._context

    async def prepare(
        self,
    ) -> None:
        """
        Build and cache the stable prompt.

        Stable content includes:

        - agent instructions
        - conversation context
        - memory
        - retrieved knowledge
        - structured output instructions
        - template-contributed messages

        Current execution messages are excluded.
        """

        state = (
            self._context.prompt_state
        )

        if state.prepared:
            return

        parts: list[str] = []

        #
        # Conversation history
        #
        prompt = (
            self._conversation_builder.build(
                self._context.conversation_context,
            )
        )

        if prompt:
            parts.append(
                prompt,
            )

        #
        # Memory
        #
        prompt = await (
            self._build_memory_prompt()
        )

        if prompt:
            parts.append(
                prompt,
            )

        #
        # Retrieved knowledge
        #
        prompt = await (
            self._build_rag_prompt()
        )

        if prompt:
            parts.append(
                prompt,
            )

        #
        # Structured output
        #
        prompt = (
            self._output_formatter.build(
                self._context.agent.output_type,
            )
        )

        if prompt:
            parts.append(
                prompt,
            )

        messages: list[ChatMessage] = []

        #
        # Stable system prompt.
        #
        if parts:

            messages.append(
                ChatMessage.system(
                    "\n\n".join(parts),
                ),
            )

        #
        # Stable template messages.
        #
        template_messages = (
            self._context.agent.prompt_template.build(
                self._context,
            )
        )

        if template_messages:

            messages.extend(
                template_messages,
            )

        #
        # Measure complete stable prompt.
        #
        stable_tokens = count_tokens_approximately(
            self._context.agent.llm.to_provider_messages(
                messages=messages,
            ),
        )

        #
        # Measure current execution messages separately.
        #
        execution_messages = [
            message
            for message in self._context.run_context.messages
            if message.content
        ]

        #
        # Store the complete stable prompt.
        #
        state.stable_messages = messages

        state.prepared = True

    async def build(
        self,
    ) -> list[ChatMessage]:
        """
        Return the prompt for the current LLM inference.

        The stable prompt is reused when already prepared.

        Only current execution messages are appended here.
        """

        await self.prepare()

        messages = [
            *self._context.prompt_state.stable_messages,
            *self._context.run_context.messages,
        ]

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
