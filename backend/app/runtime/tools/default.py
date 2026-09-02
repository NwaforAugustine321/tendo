from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar, Token
from typing import TYPE_CHECKING

from langchain_core.tools import tool

from ..agents.run_context import RunContext
from ..memory.context import MemoryContext
from ..rag.context import RAGContext

if TYPE_CHECKING:
    from ..agents.agent import Agent


_current_run_context: ContextVar[
    RunContext | None
] = ContextVar(
    "current_run_context",
    default=None,
)


def set_run_context(
    ctx: RunContext,
) -> Token[RunContext | None]:
    return _current_run_context.set(
        ctx,
    )


def reset_run_context(
    token: Token[RunContext | None],
) -> None:
    _current_run_context.reset(
        token,
    )


def get_run_context() -> RunContext:
    ctx = _current_run_context.get()

    if ctx is None:
        raise RuntimeError(
            "No active RunContext is available.",
        )

    return ctx


MEMORY_HEADER = (
    "\n[IMMUTABLE DISCLOSURE SYSTEM LONG-TERM MEMORY INSTRUCTIONS]\n\n"
    "Long-Term Memory context contains information remembered from previous"
    "conversations and interactions. It provides context about "
    "the user and their history that may no longer be present any more in the context\n\n"
    "It may contain the user's preferences, communication style, goals, "
    "interests, important personal context, previous decisions, past "
    "requests, ongoing matters, relationships, experiences, facts they "
    "have shared, and other information that is useful for understanding "
    "the user over time.\n\n"
    "Use relevant memory to inform your reasoning and response. "
    "Do not ignore relevant memory, but do not invent or assume information "
    "that is not supported by the memory.\n\n"
    "[IMMUTABLE DISCLOSURE LONG-TERM MEMORY CONTEXT]:\n"
    "{memory}\n\n"
)


RAG_HEADER = (
    "\n[IMMUTABLE DISCLOSURE SYSTEM LONG-TERM CENTRAL KNOWLEDGE INSTRUCTIONS]:\n"
    "Central Knowledge context contains accumulated business information and "
    "understanding. It may include business operations, activities, "
    "processes, data, entities, relationships, facts, evidence, findings, "
    "decisions, goals, insights, observations, patterns,perspectives, assumptions, "
    "and other established business knowledge.\n\n"
    "Use this knowledge as a central source of business information when "
    "reasoning about and performing the task\n\n"
    "Use relevant knowledge to inform your reasoning, decisions, and responses. "
    "Distinguish established information from interpretations and assumptions, "
    "and do not invent unsupported information.\n\n"
    "[IMMUTABLE DISCLOSURE SYSTEM LONG-TERM CENTRAL KNOWLEDGE CONTEXT]:\n"
    "{central_knowledge}\n\n"
)


def _format_memory(
    context: MemoryContext,
) -> str:
    if not context.entries:
        return "No relevant long-term memory was found."

    lines = []

    for entry in context.entries:
        lines.append(
            f"- {entry.text}",
        )

    lines = '\n'.join(lines)
    return MEMORY_HEADER.replace('{memory}', lines)


def _format_knowledge(
    context: RAGContext,
) -> str:
    if not context.documents:
        return "No relevant central knowledge was found."

    lines = [

    ]

    for document in context.documents:
        lines.append(
            f"- {document.content}",
        )

    lines = '\n'.join(lines)
    return RAG_HEADER.replace('{central_knowledge}', lines)


def create_memory_tool(
    *,
    agent: Agent,
) -> Callable:
    @tool(
        "search_memory",
        description=(
            """
        Search long-term memory for information relevant to the task.

        Long-term memory is the agent's persistent memory of information learned,
        remembered, or retained over time. It may contain information about the
        user, business, entities, preferences, goals, facts, experiences,
        relationships, decisions, observations, important context, and other
        durable information.

        Use this tool when the task depends on information the agent may already
        remember, regardless of where that information originally came from.

        This tool retrieves remembered information. It is not used to inspect,
        filter, query, count, aggregate, or retrieve exact records from
        structured business data.

        Use business-data tools when the task requires exact structured records,
        field values, filtering, aggregation, or relationships.

        Use knowledge search when the required information is contained in
        stored documents, evidence, or accumulated knowledge sources rather than
        the agent's long-term memory.

        Multiple searches may be used when different pieces of remembered
        information need to be retrieved or cross-referenced.
        """
        )
    )
    async def search_memory(
        query: str,
    ) -> str:

        if agent.memory is None:
            return "Long-term memory is not available."

        run_context = get_run_context()

        context = await agent.memory.retrieve(
            run_context,
            query=query,
        )

        return _format_memory(
            context,
        )

    return search_memory


def create_rag_tool(
    *,
    agent: Agent,
) -> Callable:
    @tool(
        "search_evidence",
        description=(
            """
        Search stored business knowledge and evidence for information relevant to
        the task.

        Use this tool when the task requires information contained in stored
        documents, evidence, findings, documentation, policies, processes,
        business context, explanations, decisions, observations, or other
        accumulated knowledge.

        Use this tool when the required information may be distributed across
        documents or knowledge sources and needs to be found based on its
        meaning, context, or relevance rather than an exact structured field
        value.

        This tool retrieves knowledge and evidence. It is not used to inspect,
        filter, query, count, aggregate, or retrieve exact records from
        structured business data.

        Use business-data tools when the task requires exact structured records,
        field values, filtering, aggregation, or relationships.

        Multiple searches may be used when the task requires gathering or
        cross-referencing information from different knowledge sources.
        """
        )
    )
    async def search_knowledge(
        query: str,
    ) -> str:

        if agent.rag is None:
            return "Central knowledge is not available."

        run_context = get_run_context()

        context = await agent.rag.retrieve(
            run_context,
            query=query,
        )

        return _format_knowledge(
            context,
        )

    return search_knowledge
