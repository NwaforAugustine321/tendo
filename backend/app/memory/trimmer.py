"""Message trimming logic with token counting and archival."""

import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)


class TrimResult(NamedTuple):
    retained_messages: list[dict]
    trimmed_messages: list[dict]


def count_tokens(messages: list[dict]) -> int:
    """Count approximate tokens in a list of messages.

    Uses tiktoken with fallback to character-based approximation (chars / 4).
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            # Each message has ~4 tokens overhead (role, formatting)
            total += len(enc.encode(content)) + len(enc.encode(role)) + 4
        return total
    except Exception:
        # Fallback: approximate tokens as chars / 4
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            total += (len(content) + len(role)) // 4 + 4
        return total


def identify_trimmable(messages: list[dict]) -> tuple[list[int], list[int]]:
    """Separate preserved message indices from trimmable message indices.

    Preserved:
        - System message (first message with role='system')
        - Most recent user message
        - The assistant message immediately preceding the most recent user message

    Returns:
        (preserved_indices, trimmable_indices) in their original order.
    """
    if not messages:
        return [], []

    preserved_indices: set[int] = set()

    # Preserve system message (first with role='system')
    for i, msg in enumerate(messages):
        if msg.get("role") == "system":
            preserved_indices.add(i)
            break

    # Find most recent user message
    last_user_idx = None
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            last_user_idx = i
            break

    if last_user_idx is not None:
        preserved_indices.add(last_user_idx)
        # Preserve immediately preceding assistant message
        if last_user_idx > 0 and messages[last_user_idx - 1].get("role") == "assistant":
            preserved_indices.add(last_user_idx - 1)

    preserved = sorted(preserved_indices)
    trimmable = [i for i in range(len(messages)) if i not in preserved_indices]

    return preserved, trimmable


def trim_messages_to_limit(messages: list[dict], token_limit: int) -> TrimResult:
    """Trim messages to fit within token limit.

    Strategy:
    1. Identify trimmable messages (exclude system + last exchange).
    2. If token count is within budget, return all messages unchanged.
    3. If trimmable >= 10, remove 10–20 oldest until within budget.
    4. If trimmable < 10, remove all trimmable.
    5. If removing 20 isn't enough, continue one-at-a-time.

    Returns:
        TrimResult with retained and trimmed message lists.
    """
    current_tokens = count_tokens(messages)

    # No trimming needed
    if current_tokens <= token_limit:
        return TrimResult(retained_messages=list(messages), trimmed_messages=[])

    preserved_indices, trimmable_indices = identify_trimmable(messages)

    # Nothing to trim
    if not trimmable_indices:
        return TrimResult(retained_messages=list(messages), trimmed_messages=[])

    # Determine how many to remove
    trimmed_indices: list[int] = []

    if len(trimmable_indices) < 10:
        # Remove all trimmable
        trimmed_indices = list(trimmable_indices)
    else:
        # Remove 10-20 oldest (trimmable_indices is already sorted oldest-first)
        # Start with 10, go up to 20, stop when within budget
        for batch_size in range(10, min(21, len(trimmable_indices) + 1)):
            candidate_trimmed = trimmable_indices[:batch_size]
            candidate_retained_indices = [
                i for i in range(len(messages)) if i not in set(candidate_trimmed)
            ]
            candidate_retained = [messages[i] for i in candidate_retained_indices]

            if count_tokens(candidate_retained) <= token_limit:
                trimmed_indices = candidate_trimmed
                break
        else:
            # 20 wasn't enough — take 20 and continue one-at-a-time
            trimmed_indices = trimmable_indices[:20]

            # Continue removing one-at-a-time beyond 20
            remaining_trimmable = trimmable_indices[20:]
            for idx in remaining_trimmable:
                trimmed_indices.append(idx)
                candidate_retained_indices = [
                    i for i in range(len(messages)) if i not in set(trimmed_indices)
                ]
                candidate_retained = [messages[i] for i in candidate_retained_indices]
                if count_tokens(candidate_retained) <= token_limit:
                    break

    # Build result
    trimmed_set = set(trimmed_indices)
    retained = [messages[i] for i in range(len(messages)) if i not in trimmed_set]
    trimmed = [messages[i] for i in trimmed_indices]

    return TrimResult(retained_messages=retained, trimmed_messages=trimmed)
