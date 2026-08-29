from __future__ import annotations

from app.runtime.chat.message import ChatMessage
from app.runtime.llm.llm import LLM
from app.runtime.llm_vendors.langchain import LangChainLLM
from .summarizer import Summarizer
from app.llm.client import get_client
import logging

logger = logging.getLogger(__name__)

_llm_instance = None


def _get_llm():
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = get_client()
    return _llm_instance


class DefaultSummarizer(
    Summarizer,
):
    """
    Default LLM-based summarizer.

    Can be reused for conversation, memory,
    RAG, documents, and any other message
    summarization task.
    """

    def __init__(
        self,
        *,
        llm: LLM | None = None,
        instructions: str = "",
    ) -> None:

        self._llm = (
            llm
            if llm is not None
            else LangChainLLM(model=_get_llm())
        )

        self._instructions = (
            instructions.strip()
        )

    async def summarize(
        self,
        *,
        messages: list[ChatMessage],
        target_tokens: int,
        instructions: str | None = None,
    ) -> str:

        try:

            system_prompt = (
                instructions.strip()
                if instructions is not None
                else self._instructions
            )

            prompt: list[ChatMessage] = []

            if system_prompt:

                prompt.append(
                    ChatMessage.system(
                        (
                            f"{system_prompt}\n\n"
                            f"Do not exceed approximately "
                            f"{target_tokens} tokens.\n"
                            "Return only the summary."
                        )
                    )
                )

            prompt.extend(
                ChatMessage.from_dicts(
                    ChatMessage.to_dicts(
                        messages,
                    )
                )
            )

            response = await self._llm.invoke(
                prompt,
            )

            return response.text.strip()

        except Exception as e:
            logger.info('Summarization failed:', e)
