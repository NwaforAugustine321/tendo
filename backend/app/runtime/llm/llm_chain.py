class LLMChain(LLM):

    def __init__(
        self,
        *,
        model: BaseChatModel,
    ) -> None:

        self._model = model