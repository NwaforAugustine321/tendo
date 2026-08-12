from __future__ import annotations

from .token_counter import TokenCounter
from langchain_core.messages.utils import count_tokens_approximately


class EstimatedTokenCounter(TokenCounter):
    """
    Token counter using LangChain's count_tokens_approximately.
    Accepts LangChain BaseMessage list directly.
    """

    async def count(
        self,
        messages: list,
    ) -> int:
        return count_tokens_approximately(messages)
