from __future__ import annotations

import logging

from langchain_core.messages.utils import (
    count_tokens_approximately,
)

from app.runtime.events.events import (
    EventType,
    Status,
    StatusEvent,
)
from app.runtime.chat.message import ChatMessage
from app.runtime.memory.builder import MemoryPromptBuilder
from app.runtime.prompts.sections.conversation import (
    ConversationPromptBuilder,
)
from app.runtime.prompts.sections.user_task import (
    UserTaskPromptBuilder,
)
from app.runtime.prompts.sections.tools import ToolPromptBuilder
from app.runtime.prompts.sections.runtime import RuntimePromptBuilder
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

        self._tools_builder = (
            ToolPromptBuilder()
        )

        self._runtime_builder = (RuntimePromptBuilder())

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

        parts: list[str] = []

        # Setup agent system runtime
        prompt = await self._build_runtime_prompt()

        if prompt:
            parts.append(
                prompt,
            )

        state = (
            self._context.prompt_state
        )

        if state.prepared:
            return

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

        # tools prompt
        prompt = await self._build_tool_prompt()

        if prompt:
            parts.append(
                prompt,
            )

        messages: list[ChatMessage] = []
        #
        # Other agent system instructions.
        #

        if parts:

            messages.append(
                ChatMessage.system(
                    "\n\n".join(parts),
                ),
            )

        #
        # Default agent stystem instructions.
        #
        agent_instructions = (
            self._context.agent.prompt_template.build(
                self._context
            )
        )

        if agent_instructions:

            messages.extend(
                agent_instructions,
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

        await self._context.run_context.emitter.emit(
            EventType.PROGRESS,
            StatusEvent(
                status=Status.RETRIEVING,
            ),
        )

        memory = await agent.memory.retrieve(
            self._context.run_context,
        )

        await self._context.run_context.emitter.emit(
            EventType.PROGRESS,
            StatusEvent(
                status=Status.REASONING,
            ),
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

        await self._context.run_context.emitter.emit(
            EventType.PROGRESS,
            StatusEvent(
                status=Status.RETRIEVING,
            ),
        )

        knowledge = await agent.rag.retrieve(
            self._context.run_context,
        )

        await self._context.run_context.emitter.emit(
            EventType.PROGRESS,
            StatusEvent(
                status=Status.REASONING,
            ),
        )

        return self._rag_builder.build(
            knowledge,
        )

    async def _build_tool_prompt(
        self,
    ) -> str:

        tools = self._context.agent\
            .tool_context\
            .proxy.tools

        if not tools:
            return ""

        return self._tools_builder.build(
            self._context.agent
            .tool_context
            .tool_to_string(tools=tools)
        )

    async def _build_runtime_prompt(
        self,
        runtime_inject_payload: list[dict[str, str]] | None = []
    ) -> str:

        default_runtime = [
            {
                "key": "max_iterations",
                "value": str(self._context.agent._max_iterations),
            }
        ]

        default_runtime.extend(runtime_inject_payload)

        return self._runtime_builder.build(
            runtime_inject_payload=default_runtime
        )
