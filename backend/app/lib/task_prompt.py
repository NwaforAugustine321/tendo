"""Task prompt builder — assembles prompts using i18n slices from app/translations/en.json.

Follows CrewAI's pattern: pull template from translations slices,
then .format() the actual values into it.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from app.lib.i18n import _get_i18n
from app.lib.pydantic_schema_utils import generate_model_description

if TYPE_CHECKING:
    from app.memory.memory import Memory

logger = logging.getLogger(__name__)


def _slice(key: str) -> str:
    """Get a raw prompt slice template from translations."""
    i18n = _get_i18n()
    return i18n.get(f"slices.{key}")


async def rewrite_query(task_prompt: str) -> str:
    """Rewrite a task prompt into an optimized vector search query using LLM."""
    from app.llm.client import get_client

    try:
        i18n = _get_i18n()
        rewriter_prompt = i18n.get("slices.knowledge_search_query_system_prompt")
        query_template = i18n.get("slices.knowledge_search_query")
        query = query_template.format(task_prompt=task_prompt)

        llm = get_client()
        messages = [
            {"role": "system", "content": rewriter_prompt},
            {"role": "user", "content": query},
        ]
        response = await llm.ainvoke(messages)
        search_query = response.content.strip() if response.content else task_prompt

        return search_query if search_query else task_prompt

    except Exception as e:
        logger.warning(f"Query rewriting failed: {e}")
        return task_prompt


def prompt(
    description: str,
    expected_output: str | None = None,
    chat_history: list[dict] | None = None,
) -> str:
    """
    Build a structured task prompt by pulling i18n slices and injecting values.

    Uses templates from app/translations/en.json under "slices" key.

    Usage:
        prompt = build_task_prompt(
            description="Record a sale for {customer_name}",
            expected_output="Confirm the transaction details before saving.",
            chat_history=[{"role": "user", "content": "I sold wine"}],
        )
    """


    # Pull "task" slice: uses {input} placeholder
    task_slice = _slice("task")
    parts = [task_slice.format(input=description)]


    # Chat history: uses "conversation_history_instruction" slice
    if chat_history:
        instruction = _slice("conversation_history_instruction")
        history_lines = "\n".join(
            f"{msg['role'].capitalize()}: {msg['content']}"
            for msg in chat_history
            if isinstance(msg, dict) and "role" in msg and "content" in msg
        )
        parts.append(f"{instruction}\n\n{history_lines}")

    # Expected output: uses "expected_output" slice with {expected_output}
    if expected_output:
        output_slice = _slice("expected_output")
        parts.append(output_slice.format(expected_output=expected_output))

    return "\n\n".join(parts)


def build_task_prompt_with_schema(
    task_prompt: str,
    output_json: type | None = None,
    output_pydantic: type | None = None,
    response_model: type | None = None,
) -> str:
    """Build task prompt with JSON/Pydantic schema instructions if applicable.

    Args:
        task_prompt: The initial task prompt.
        output_json: A Pydantic model class for JSON output format.
        output_pydantic: A Pydantic model class for structured output.
        response_model: If set, schema instructions are skipped (handled by provider).

    Returns:
        The task prompt potentially augmented with schema instructions.
    """
    if (output_json or output_pydantic) and not response_model:
        if output_json:
            schema_dict = generate_model_description(output_json)
            schema = json.dumps(schema_dict["json_schema"]["schema"], indent=2)
            task_prompt += "\n" + _slice("formatted_task_instructions").format(
                output_format=schema
            )
        elif output_pydantic:
            schema_dict = generate_model_description(output_pydantic)
            schema = json.dumps(schema_dict["json_schema"]["schema"], indent=2)
            task_prompt += "\n" + _slice("formatted_task_instructions").format(
                output_format=schema
            )
    return task_prompt


def format_task_with_context(task_prompt: str, context: str | None) -> str:
    """
    Format task prompt with context if provided.

    Uses "task_with_context" slice with {task} and {context}.
    """
    if context:
        task_with_context = _slice("task_with_context")
        return task_with_context.format(task=task_prompt, context=context)
    return task_prompt


async def retrieve_memory_context(
    task_prompt: str,
    query: str,
    memory: Memory | None = None,
    limit: int = 5,
) -> str:
    """Retrieve memory context and append it to the task prompt.

    Queries the Memory store (LanceDB) for relevant past conversations
    using composite scoring (semantic + recency + importance).
    Injects results using the "memory" i18n slice with {memory} placeholder.

    Args:
        task_prompt: The current task prompt.
        query: The search query (usually the task description).
        memory: A Memory instance to query. If None, returns unchanged.
        limit: Maximum number of memory results to retrieve.

    Returns:
        The task prompt, potentially augmented with memory context.
    """
    if memory is None:
        return task_prompt

    matches = await memory.recall(query, limit=limit)

    if not matches:
        return task_prompt

    # Format memory results
    memory_text = "\n".join(m.format() for m in matches)

    if memory_text.strip():
        task_prompt += _slice("memory").format(memory=memory_text)

    return task_prompt


async def retrieve_knowledge_context(
    task_prompt: str,
    knowledge: Any | None = None,
    n_results: int = 5,
) -> str:
   
    if knowledge is None:
        return task_prompt

    try:
        search_query = await rewrite_query(task_prompt)

        if not search_query:
            return task_prompt

        results = await knowledge.query(search_query, n_results=n_results)

        if not results:
            return task_prompt

        valid_snippets = [
            item["text"]
            for item in results
            if item and item.get("text")
        ]

        if valid_snippets:
            snippet = "\n".join(valid_snippets)
            task_prompt += f"\n\nAdditional Information: {snippet}"

    except Exception as e:
        logger.warning(f"Knowledge retrieval failed: {e}")

    return task_prompt


async def prepare_task_prompt(
    description: str,
    expected_output: str | None = None,
    chat_history: list[dict] | None = None,
    context: str | None = None,
    output_json: type | None = None,
    output_pydantic: type | None = None,
    response_model: type | None = None,
    knowledge: Any | None = None,
    memory: Memory | None = None,
    n_results: int = 5,
    memory_limit: int = 5,
) -> str:
    """Build a complete task prompt in one call: base prompt → schema → context → memory → knowledge.

    Combines prompt, build_task_prompt_with_schema,
    format_task_with_context, retrieve_memory_context, and
    retrieve_knowledge_context into a single entry point.

    Returns:
        The fully assembled task prompt ready for LLM execution.
    """
    # 1. Build base task prompt with description, chat history, expected output
    task_prompt = prompt(
        description=description,
        expected_output=expected_output,
        chat_history=chat_history,
    )

    # 2. Append schema instructions if output model is specified
    task_prompt = build_task_prompt_with_schema(
        task_prompt=task_prompt,
        output_json=output_json,
        output_pydantic=output_pydantic,
        response_model=response_model,
    )

    # 3. Wrap with context if provided
    task_prompt = format_task_with_context(task_prompt, context)

    # 4. Retrieve and append memory context (LanceDB — conversation memory)
    task_prompt = await retrieve_memory_context(
        task_prompt=task_prompt,
        query=description,
        memory=memory,
        limit=memory_limit,
    )

    return task_prompt
