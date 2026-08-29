"""Tool factory — converts plain async functions into LangChain StructuredTools."""

from typing import Callable

from langchain_core.tools import StructuredTool
from pydantic import BaseModel


def make_tool(
    func: Callable,
    name: str,
    description: str,
    args_schema: type[BaseModel] | None = None,
) -> StructuredTool:
    """Convert an async function into a LangChain StructuredTool""

    return StructuredTool.from_function(
        coroutine=func,
        name=name,
        description=description,
        args_schema=args_schema,
    )
