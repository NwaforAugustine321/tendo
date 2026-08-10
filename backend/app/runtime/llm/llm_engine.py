from __future__ import annotations
from langchain_core.language_models import BaseChatModel
from app.runtime.chat.context import ChatContext
from .inference_stream import (
    InferenceMode,
    InferenceStream,
)
from .llm import LLM


class LLMEngine(LLM):

    def __init__(
        self,
        *,
        model: BaseChatModel,
        mode: InferenceMode = InferenceMode.STREAM,
    ) -> None:

        self._model = model
        self._mode = mode

    @property
    def model(
        self,
    ) -> BaseChatModel:
        return self._model

    @property
    def mode(
        self,
    ) -> InferenceMode:
        return self._mode

    def chat(
        self,
        chat_context: ChatContext,
    ) -> InferenceStream:
        """
        Create a new inference.
        """

        return InferenceStream(
            model=self._model,
            chat_context=chat_context,
            mode=self._mode,
        )
