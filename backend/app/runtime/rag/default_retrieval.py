from __future__ import annotations

import logging

from app.runtime.agents.run_context import RunContext

from .retrieval import RetrievalEngine


logger = logging.getLogger(__name__)


HISTORY_MESSAGES = 8

HISTORY_MESSAGE_CHARS = 500


REWRITE_QUERY_PROMPT = """
Rewrite the message into a concise semantic retrieval query for context information relevant to the current objective.

Use the conversation context to understand what the message refers to. Resolve pronouns, references,
and omitted subjects when the context makes them clear. Preserve exact names, entities, dates, and
quantities from the context.

If the message depends on information established in the context, include the resolved information
in the query. If it is already self-contained, preserve its meaning without unnecessary changes.

Focus on the information that needs to be retrieved, not the action being performed.
Do not add assumptions or information not supported by the context.

<Context>:
{context}

Return one plain-text query (30-50 max-word). No explanation.
"""


class DefaultRetrieval(
    RetrievalEngine,
):
    """
    Default retrieval strategy.

    Builds a search query from the current user request,
    resolving it against the conversation on the RunContext and
    rewriting it into focused search phrases for better
    semantic retrieval.
    """

    async def build_query(
        self,
        ctx: RunContext,
    ) -> str:

        return await self._rewrite_query(ctx)

    def _run_context(
        self,
        ctx: RunContext,
    ) -> str:
        """
        Messages from the current run, as a context block.

        System and tool messages are skipped. System messages are
        instructions, and a tool message carries a tool_call_id
        that this standalone call cannot match.
        """

        lines: list[str] = []

        for message in ctx.messages[-HISTORY_MESSAGES:]:

            if not message.content:
                continue

            role = str(
                getattr(
                    message.role,
                    "value",
                    message.role,
                ),
            )

            if role not in ("user", "assistant"):
                continue

            content = message.content

            if not isinstance(content, str):
                content = str(content)

            content = content.strip()

            if len(content) > HISTORY_MESSAGE_CHARS:
                content = (
                    content[:HISTORY_MESSAGE_CHARS] + "..."
                )

            lines.append(
                f"<{role}>: {content}",
            )

        return "\n".join(lines)

    async def _rewrite_query(
        self,
        ctx: RunContext,
    ) -> str:
        """
        Use the executing agent's LLM to rewrite the user query
        into focused search phrases for RAG retrieval.

        """

        query = (ctx.user_request or "").strip()

        if not query:
            return ""

        llm = ctx.session._agent._llm

        model = (
            getattr(llm, "base_model", None)
            or getattr(llm, "model", None)
        )

        if model is None:
            return query

        messages = [
            {
                "role": "system",
                "content": REWRITE_QUERY_PROMPT.format(
                    context=(
                        self._run_context(ctx)
                        or "(no additional context)"
                    ),
                ),
            },
            {
                "role": "user",
                "content": query,
            },
        ]

        try:
            response = await model.ainvoke(messages)

            content = getattr(
                response,
                "content",
                str(response),
            )

            if isinstance(content, list):
                content = "".join(
                    str(p)
                    for p in content
                )

            rewritten = str(content).strip()

            return rewritten if rewritten else query

        except Exception:
            logger.debug(
                "RAG query rewrite skipped.",
                exc_info=True,
            )
            return query
