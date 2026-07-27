from __future__ import annotations

import logging
import re
from typing import Any, List, Dict

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


def is_context_length_exceeded(exception: Exception) -> bool:
    """Check if the exception is due to context length exceeding."""
    error_str = str(exception).lower()
    return any(pattern in error_str for pattern in _CONTEXT_LENGTH_PATTERNS)


def _get_model_context_length(llm: Any) -> int:
    """Safely extracts context limits with strict fallback validation."""
    # Check LangChain explicit properties or common fields first
    for attr in ("max_tokens", "n_ctx", "model_max_tokens", "context_window"):
        val = getattr(llm, attr, None)
        if isinstance(val, int) and val > 1000:
            return val

    # Explore dictionary metadata layouts
    metadata = {}
    for attr in ("metadata", "model_kwargs", "_default_params"):
        metadata.update(getattr(llm, attr, None) or {})

    for key in ("max_tokens", "context_length", "n_ctx"):
        val = metadata.get(key)
        if isinstance(val, int) and val > 1000:
            return val

    # Safe global default boundary fallback
    return 4096


def _format_messages_for_summary(messages: List[Dict[str, Any]]) -> str:
    """Format messages with role labels for summarization."""
    lines: List[str] = []
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

        label = f"[{role.upper()}]:"
        lines.append(f"{label} {content}")

    return "\n\n".join(lines)


def _extract_summary_tags(text: str) -> str:
    """Extract content between <summary></summary> tags."""
    match = re.search(r"<summary>(.*?)</summary>", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


async def summarize_messages(
    messages: List[Dict[str, Any]], max_context_tokens: int = None
) -> List[Any]:
    """Summarizes context systematically while protecting newer context elements.

    Uses LangChain's native token tracking method to guarantee accuracy
    across different model providers. Returns LangChain message objects.
    """
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from app.llm.client import get_client

    llm = get_client()

    if max_context_tokens is None:
        max_context_tokens = _get_model_context_length(llm)

    system_messages = [m for m in messages if m.get("role") == "system"]
    non_system_messages = [m for m in messages if m.get("role") != "system"]

    if not non_system_messages:
        return _to_langchain_messages(messages)

    # Helper to calculate total tokens using LangChain's native API
    def calculate_current_tokens(sys_msgs, ns_msgs) -> int:
        full_text = "".join(str(m.get("content", "")) for m in (sys_msgs + ns_msgs))
        try:
            return llm.get_num_tokens(full_text)
        except Exception:
            # Fallback scaling if method fails or model doesn't support local tokenization
            return len(full_text) // 4

    total_tokens = calculate_current_tokens(system_messages, non_system_messages)

    # Process if boundary is exceeded
    while total_tokens > max_context_tokens and len(non_system_messages) > 1:
        # Target roughly half or up to 10 messages for summarization chunk
        num_to_summarize = min(10, max(2, len(non_system_messages) // 2))
        old_messages = non_system_messages[:num_to_summarize]
        recent_messages = non_system_messages[num_to_summarize:]

        conversation_text = _format_messages_for_summary(old_messages)
        chunk_tokens = calculate_current_tokens([], [{"content": conversation_text}])

        # Scale down chunk execution window if too big for the prompt
        while chunk_tokens > (max_context_tokens - 500) and num_to_summarize > 1:
            num_to_summarize = max(1, num_to_summarize // 2)
            old_messages = non_system_messages[:num_to_summarize]
            recent_messages = non_system_messages[num_to_summarize:]
            conversation_text = _format_messages_for_summary(old_messages)
            chunk_tokens = calculate_current_tokens([], [{"content": conversation_text}])

        # Invoke summarizing step
        prompt = f"Summarize the core context concisely inside <summary> tags:\n\n{conversation_text}"
        try:
            response = await llm.ainvoke(prompt)
            summary_content = _extract_summary_tags(
                response.content if hasattr(response, "content") else str(response)
            )
        except Exception as e:
            logger.error(f"Summarization processing error: {e}")
            raise

        summary_msg = {
            "role": "system",
            "content": f"Summary of earlier conversation: {summary_content}",
        }

        # Reconstruct history stack layout dynamically
        non_system_messages = [summary_msg] + recent_messages

        # Recalculate token states to prevent infinite loop execution
        total_tokens = calculate_current_tokens(system_messages, non_system_messages)

    return _to_langchain_messages(system_messages + non_system_messages)


def _to_langchain_messages(messages: List[Dict[str, Any]]) -> List[Any]:
    """Convert dict messages back to LangChain message objects."""
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    converted = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            converted.append(SystemMessage(content=content))
        elif role == "assistant":
            converted.append(AIMessage(content=content))
        else:
            converted.append(HumanMessage(content=content))
    return converted


async def handle_text_context_length(text: str, max_tokens: int = None) -> str:
    """Trim text to fit within context length if needed."""
    from app.llm.client import get_client

    llm = get_client()

    if max_tokens is None:
        max_tokens = _get_model_context_length(llm)

    try:
        token_count = llm.get_num_tokens(text)
    except Exception:
        token_count = len(text) // 4

    if token_count <= max_tokens:
        return text

    # Truncate to fit — estimate chars per token and trim
    ratio = max_tokens / token_count
    target_chars = int(len(text) * ratio * 0.9)  # 90% to leave headroom
    return text[:target_chars]


# Alias for backward compatibility
handle_context_length = handle_text_context_length
