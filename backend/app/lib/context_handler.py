"""Context window handling — summarizes messages when context length is exceeded.

Mirrors CrewAI's handle_context_length pattern:
1. Catch context length exceeded error
2. Split messages into chunks
3. Use LLM to summarize each chunk
4. Replace non-system messages with the summary

Uses summarizer_system_message and summarize_instruction i18n slices.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.lib.i18n import _get_i18n

logger = logging.getLogger(__name__)

# Common error patterns indicating context length exceeded
_CONTEXT_LENGTH_PATTERNS = [
    "maximum context length",
    "context length exceeded",
    "context_length_exceeded",
    "context window full",
    "too many tokens",
    "max_tokens",
    "token limit",
    "prompt is too long",
    "request too large",
    "content too large",
    "maximum number of tokens",
    "input is too long",
]


def _slice(key: str) -> str:
    """Get a raw prompt slice template from translations."""
    i18n = _get_i18n()
    return i18n.get(f"slices.{key}")


def is_context_length_exceeded(exception: Exception) -> bool:
    """Check if the exception is due to context length exceeding.

    Args:
        exception: The exception to check.

    Returns:
        True if the exception is due to context length being exceeded.
    """
    error_str = str(exception).lower()
    return any(pattern in error_str for pattern in _CONTEXT_LENGTH_PATTERNS)


def _estimate_token_count(text: str) -> int:
    """Estimate token count using a conservative heuristic (1 token ≈ 4 chars).

    Args:
        text: The text to estimate tokens for.

    Returns:
        Estimated token count.
    """
    return len(text) // 4


def _format_messages_for_summary(messages: list[dict[str, Any]]) -> str:
    """Format messages with role labels for summarization.

    Skips system messages. Handles None content, tool_calls, and
    multimodal content blocks.

    Args:
        messages: List of messages to format.

    Returns:
        Role-labeled conversation text.
    """
    lines: list[str] = []
    for msg in messages:
        role = msg.get("role", "user")
        if role == "system":
            continue

        content = msg.get("content")
        if content is None:
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                tool_names = [
                    tc.get("name", "unknown") if isinstance(tc, dict) else "unknown"
                    for tc in tool_calls
                ]
                content = f"[Called tools: {', '.join(tool_names)}]"
            else:
                content = ""
        elif isinstance(content, list):
            text_parts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            content = " ".join(text_parts) if text_parts else "[multimodal content]"

        if role == "assistant":
            label = "[ASSISTANT]:"
        elif role == "tool":
            tool_name = msg.get("name", "unknown")
            label = f"[TOOL_RESULT ({tool_name})]:"
        else:
            label = "[USER]:"

        lines.append(f"{label} {content}")

    return "\n\n".join(lines)


def _split_messages_into_chunks(
    messages: list[dict[str, Any]], max_tokens: int = 4000
) -> list[list[dict[str, Any]]]:
    """Split messages into chunks at message boundaries.

    Excludes system messages from chunks. Each chunk stays under
    max_tokens based on estimated token count.

    Args:
        messages: List of messages to split.
        max_tokens: Maximum estimated tokens per chunk.

    Returns:
        List of message chunks.
    """
    non_system = [m for m in messages if m.get("role") != "system"]
    if not non_system:
        return []

    chunks: list[list[dict[str, Any]]] = []
    current_chunk: list[dict[str, Any]] = []
    current_tokens = 0

    for msg in non_system:
        content = msg.get("content")
        if content is None:
            msg_text = ""
        elif isinstance(content, list):
            msg_text = str(content)
        else:
            msg_text = str(content)

        msg_tokens = _estimate_token_count(msg_text)

        if current_chunk and (current_tokens + msg_tokens) > max_tokens:
            chunks.append(current_chunk)
            current_chunk = []
            current_tokens = 0

        current_chunk.append(msg)
        current_tokens += msg_tokens

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _extract_summary_tags(text: str) -> str:
    """Extract content between <summary></summary> tags.

    Falls back to the full text if no tags are found.

    Args:
        text: Text potentially containing summary tags.

    Returns:
        Extracted summary content, or full text if no tags found.
    """
    match = re.search(r"<summary>(.*?)</summary>", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


async def summarize_messages(messages: list[dict[str, Any]], max_chunk_tokens: int = 4000) -> None:
    """Summarize messages to fit within context window.

    Uses structured context compaction: preserves system messages,
    splits at message boundaries, formats with role labels, and
    produces structured summaries for seamless task continuation.

    Modifies messages list IN-PLACE — replaces non-system messages
    with a single summarized message.

    Args:
        messages: List of messages to summarize (modified in-place).
        max_chunk_tokens: Max estimated tokens per chunk for splitting.
    """
    from app.llm.client import get_client

    system_messages = [m for m in messages if m.get("role") == "system"]
    non_system_messages = [m for m in messages if m.get("role") != "system"]

    if not non_system_messages:
        return

    chunks = _split_messages_into_chunks(non_system_messages, max_chunk_tokens)
    llm = get_client()

    summarized_contents: list[str] = []

    for chunk in chunks:
        conversation_text = _format_messages_for_summary(chunk)
        summarization_messages = [
            {"role": "system", "content": _slice("summarizer_system_message")},
            {
                "role": "user",
                "content": _slice("summarize_instruction").format(
                    conversation=conversation_text
                ),
            },
        ]

        try:
            response = await llm.ainvoke(summarization_messages)
            summary = response.content.strip() if response.content else ""
            extracted = _extract_summary_tags(summary)
            summarized_contents.append(extracted)
        except Exception as e:
            logger.warning(f"Failed to summarize chunk: {e}")
            # Fall back to just keeping the last few messages of the chunk
            fallback = _format_messages_for_summary(chunk[-3:])
            summarized_contents.append(fallback)

    merged_summary = "\n\n".join(summarized_contents)

    # Replace messages in-place (same as CrewAI)
    messages.clear()
    messages.extend(system_messages)
    messages.append({
        "role": "user",
        "content": _slice("summary").format(merged_summary=merged_summary),
    })

    logger.info(f"Context summarized: {len(non_system_messages)} messages → 1 summary")


async def handle_context_length(
    messages: list[dict[str, Any]],
    respect_context_window: bool = True,
) -> None:
    """Handle context length exceeded by summarizing or raising.

    Args:
        messages: List of messages to summarize (modified in-place).
        respect_context_window: Whether to summarize or raise.

    Raises:
        SystemExit: If respect_context_window is False.
    """
    if respect_context_window:
        logger.warning("Context length exceeded. Summarizing messages...")
        await summarize_messages(messages)
    else:
        raise SystemExit(
            "Context length exceeded. Consider enabling respect_context_window=True."
        )


async def handle_text_context_length(content: str, max_chunk_tokens: int = 4000) -> str:
    """Handle long text content by splitting into chunks and summarizing progressively.

    If content fits within max_chunk_tokens, returns it as-is.
    Otherwise splits using langchain text splitter, summarizes each via LLM, and merges.

    Args:
        content: Raw text content to fit within context limits.
        max_chunk_tokens: Max estimated tokens per chunk.

    Returns:
        Content that fits within context limits (original or summarized).
    """
    from app.llm.client import get_client
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    if not content or not content.strip():
        return content

    estimated_tokens = len(content) // 4
    if estimated_tokens <= max_chunk_tokens:
        return content

    max_chars = max_chunk_tokens * 4
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chars,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(content)

    llm = get_client()
    summarized_parts: list[str] = []

    for chunk in chunks:
        messages = [
            {"role": "system", "content": "You are a text summarizer. Produce a concise summary preserving all key facts, names, amounts, dates, and business-relevant details."},
            {"role": "user", "content": f"Summarize this text:\n\n{chunk}"},
        ]

        try:
            response = await llm.ainvoke(messages)
            summary = response.content.strip() if response.content else chunk[:1000]
            summarized_parts.append(summary)
        except Exception as e:
            logger.warning(f"Failed to summarize text chunk: {e}")
            summarized_parts.append(chunk[:1000])

    return "\n\n".join(summarized_parts)
