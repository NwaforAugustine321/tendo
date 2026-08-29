from .adapter import ToolAdapter


class LangChainAdapter(ToolAdapter):

    def __init__(self, tool):
        self.tool = tool

    @classmethod
    def supports(cls, tool):

        try:
            from langchain_core.tools import BaseTool
            return isinstance(tool, BaseTool)
        except ImportError as e:

            return False

    @property
    def name(self):
        return self.tool.name

    @property
    def id(self):
        return self.tool.name

    @property
    def description(self):
        return self.tool.description

    @property
    def args_schema(self):
        return self.tool.args_schema

    def invoke(self, arguments):
        return self.tool.invoke(arguments)

    async def ainvoke(self, arguments):
        return await self.tool.ainvoke(arguments)
