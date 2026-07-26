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
    """Estimate token count using tiktoken (cl100k_base encoding).

    Args:
        text: The text to estimate tokens for.

    Returns:
        Token count.
    """
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def _get_model_context_length(llm) -> int:
    """Get the model's max context length from the LLM client.

    Tries common attributes used by different LLM providers.
    Falls back to 128000 if unable to detect.

    Args:
        llm: The LangChain LLM client instance.

    Returns:
        Max context token length for the model.
    """
    # Try common attributes
    for attr in ("max_tokens", "n_ctx", "model_max_tokens", "context_window"):
        val = getattr(llm, attr, None)
        if val and isinstance(val, int) and val > 1000:
            return val

    # Try metadata dict
    metadata = getattr(llm, "metadata", None) or getattr(llm, "model_kwargs", None) or {}
    if isinstance(metadata, dict):
        for key in ("max_tokens", "context_length", "n_ctx"):
            val = metadata.get(key)
            if val and isinstance(val, int) and val > 1000:
                return val

    # Default fallback - use smallest safe context size
    return 4096 


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


async def summarize_messages(messages: list[dict[str, Any]], max_context_tokens: int = None) -> list[dict[str, Any]]:
    """Summarize oldest messages to fit within context window, preserving newer messages.

    Returns a new compacted messages list. Does NOT modify the original.

    Args:
        messages: List of messages that exceeded context.
        max_context_tokens: Max input token limit. If None, auto-detected from LLM.

    Returns:
        New compacted messages list ready for LLM.
    """
    from app.llm.client import get_client

    llm = get_client()

    # Auto-detect context length from the LLM if not provided
    if max_context_tokens is None:
        max_context_tokens = _get_model_context_length(llm)

    system_messages = [m for m in messages if m.get("role") == "system"]
    non_system_messages = [m for m in messages if m.get("role") != "system"]

    if not non_system_messages:
        return list(messages)

    # Calculate total tokens using tiktoken
    total_text = "".join(str(m.get("content", "")) for m in (system_messages + non_system_messages))
    total_tokens = _estimate_token_count(total_text)

    if total_tokens <= max_context_tokens:
        return list(messages)

    llm = get_client()

    # Keep summarizing oldest messages until total fits under max_context_tokens
    iteration = 0

    while total_tokens > max_context_tokens and len(non_system_messages) > 1:
        iteration += 1

        # Take oldest chunk of messages (up to 10 at a time)
        num_to_summarize = min(10, max(3, len(non_system_messages) // 2))
        old_messages = non_system_messages[:num_to_summarize]
        recent_messages = non_system_messages[num_to_summarize:]

        # Format old messages for summarization
        conversation_text = _format_messages_for_summary(old_messages)

        # Check if chunk exceeds model context — reduce chunk size if needed
        chunk_tokens = _estimate_token_count(conversation_text)
        if chunk_tokens > max_context_tokens - 500:
            # Chunk is too large for the summarizer itself — take fewer messages
            while chunk_tokens > max_context_tokens - 500 and num_to_summarize > 1:
                num_to_summarize = num_to_summarize // 2
                old_messages = non_system_messages[:num_to_summarize]
                recent_messages = non_system_messages[num_to_summarize:]
                conversation_text = _format_messages_for_summary(old_messages)
                chunk_tokens = _estimate_token_count(conversation_text)

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
            extracted = _extract_summary_tags(summary) if summary else conversation_text[:500]
        except Exception as e:
            logger.warning(f"Failed to summarize oldest messages: {e}")
            extracted = f"[Previous conversation summary unavailable - {num_to_summarize} messages removed]"

        summary_msg = {
            "role": "user",
            "content": _slice("summary").format(merged_summary=extracted),
        }
        non_system_messages = [summary_msg] + recent_messages

        total_text = "".join(
            str(m.get("content", "")) for m in (system_messages + non_system_messages)
        )
        total_tokens = _estimate_token_count(total_text)

    # Return new compacted list
    result = system_messages + non_system_messages
    logger.info(f"Context compacted in {iteration} iterations, {total_tokens} tokens remaining (reduced from original)")
    logger.info(f"  Reduced token size: {total_tokens} | Messages: {len(result)}")
    return result


async def handle_context_length(
    messages: list[dict[str, Any]],
    respect_context_window: bool = True,
) -> list[dict[str, Any]]:
    """Handle context length exceeded by summarizing older messages.

    Returns a new compacted messages list (does not modify original).

    Args:
        messages: List of messages that exceeded context.
        respect_context_window: Whether to summarize or raise.

    Returns:
        New compacted messages list ready for the LLM.

    Raises:
        SystemExit: If respect_context_window is False.
    """
    if respect_context_window:
        logger.warning("Context length exceeded. Summarizing messages...")
        return await summarize_messages(messages)
    else:
        raise SystemExit(
            "Context length exceeded. Consider enabling respect_context_window=True."
        )


async def handle_text_context_length(content: str, max_tokens: int = 4000, _depth: int = 0) -> str:
    """Handle long text content by splitting into chunks, summarizing each via LLM, and merging.

    Uses recursive reduction with max depth to prevent infinite loops.

    Args:
        content: Raw text content to fit within context limits.
        max_tokens: Max token length for the LLM context (model's limit).
        _depth: Internal recursion counter (do not pass manually).

    Returns:
        Content that fits within context limits (original or summarized).
    """
    from app.llm.client import get_client
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    MAX_DEPTH = 3
    BUFFER = 500  # token buffer to stay safely under limit

    if not content or not content.strip():
        return content

    target_tokens = max_tokens - BUFFER
    estimated_tokens = _estimate_token_count(content)
    if estimated_tokens <= target_tokens:
        return content

    # Safety: if max depth reached, raise error
    if _depth >= MAX_DEPTH:
        logger.error(f"Context summarization reached max depth {MAX_DEPTH}, content still too large")
        raise RuntimeError("Failed to reduce content within max recursion depth")

    # Determine chunk size dynamically based on content length and target
    num_chunks_needed = max(2, estimated_tokens // target_tokens)
    chunk_size = max(1000, len(content) // num_chunks_needed)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(content)

    # Determine max summary words per chunk to fit target
    max_summary_words = max(50, (target_tokens * 4) // (len(chunks) * 6))

    llm = get_client()
    summarized_parts: list[str] = []

    MAX_RETRIES = 2

    for chunk in chunks:
        messages = [
            {"role": "system", "content": f"You are a text summarizer. Produce a concise summary in under {max_summary_words} words preserving key facts, names, amounts, dates."},
            {"role": "user", "content": f"Summarize:\n\n{chunk}"},
        ]

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await llm.ainvoke(messages)
                summary = response.content.strip() if response.content else ""
                if summary:
                    summarized_parts.append(summary)
                    break
                # Empty response — retry
                if attempt < MAX_RETRIES:
                    logger.warning(f"LLM returned empty summary, retrying ({attempt + 1}/{MAX_RETRIES})")
            except Exception as e:
                if attempt < MAX_RETRIES:
                    logger.warning(f"Chunk summarization failed (attempt {attempt + 1}): {e}, retrying...")
                else:
                    logger.warning(f"Chunk summarization failed after {MAX_RETRIES + 1} attempts: {e}")

    if not summarized_parts:
        raise RuntimeError("All chunk summarizations failed")

    result = "\n\n".join(summarized_parts)

    # Verify result fits within target (max_tokens - buffer)
    result_tokens = _estimate_token_count(result)
    if result_tokens <= target_tokens:
        return result

    # Recurse with increased depth
    return await handle_text_context_length(result, max_tokens, _depth + 1)
