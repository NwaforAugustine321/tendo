class CallableAdapter(ToolAdapter):

    def __init__(self, fn):
        self.fn = fn

    @classmethod
    def supports(cls, tool):
        return callable(tool)

    @property
    def name(self):
        return self.fn.__name__

    @property
    def description(self):
        return self.fn.__doc__ or ""

    @property
    def args_schema(self):
        return function_arguments_to_pydantic_model(self.fn)

    def invoke(self, arguments):
        return self.fn(**arguments)

    async def ainvoke(self, arguments):

        if inspect.iscoroutinefunction(self.fn):
            return await self.fn(**arguments)

        return self.fn(**arguments)
