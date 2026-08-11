from __future__ import annotations

import asyncio
import functools
import inspect
import json
import logging
import re
from functools import cached_property
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from enum import Flag, auto
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Generic,
    Literal,
    ParamSpec,
    Protocol,
    TypedDict,
    TypeGuard,
    TypeVar,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

import json_repair
import pydantic
from pydantic import BaseModel, create_model
from pydantic.fields import Field, FieldInfo
from pydantic_core import PydanticUndefined, from_json
from typing_extensions import NotRequired, Self, TypeAlias
from .adapter.adapter import ToolAdapter
from .adapter.langchain_adapter import LangChainAdapter
from .strategy import (
    BM25SearchStrategy,
    KeywordSearchStrategy,
    SearchItem,
    SearchStrategy,
)
from .utils import (  # noqa: E402
    function_arguments_to_pydantic_model,
    is_context_type,
    parse_function_arguments,
    prepare_function_arguments,
)

logger = logging.getLogger(__name__)

RunContext = Any


class ToolError:
    pass


_T = TypeVar("_T")
_InfoT = TypeVar("_InfoT", bound=Any)
_P = ParamSpec("_P")
_R = TypeVar("_R", bound=Awaitable[Any])


class NotGiven:
    __slots__ = ()

    def __bool__(self) -> Literal[False]:
        return False

    def __repr__(self) -> str:
        return "NOT_GIVEN"

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> Any:
        from pydantic_core import core_schema

        return core_schema.is_instance_schema(cls)


NotGivenOr: TypeAlias = _T | NotGiven
NOT_GIVEN = NotGiven()


class ToolFlag(Flag):
    NONE = 0
    IGNORE_ON_ENTER = auto()
    CANCELLABLE = auto()


class Tool(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        ...


class ProviderTool(Tool):

    _registry: list[type[ToolAdapter]] = []

    @classmethod
    def register_adapter(cls, adapter: type[ToolAdapter]):
        cls._registry.append(adapter)

    def __init__(self, tool: Any | None = None):

        if tool:
            for adapter_cls in self._registry:
                if adapter_cls.supports(tool):
                    self._adapter = adapter_cls(tool)
                    return
            raise TypeError(
                f"No adapter found for {type(tool).__name__}"
            )

    @property
    def id(self):
        return self.name

    @property
    def name(self):
        return self._adapter.name

    @property
    def description(self):
        return self._adapter.description

    @property
    def args_schema(self):
        return self._adapter.args_schema

    def invoke(self, arguments):
        return self._adapter.invoke(arguments)

    async def ainvoke(self, arguments):
        return await self._adapter.ainvoke(arguments)

    @classmethod
    def supports(cls, tool: Any) -> bool:
        return any(adapter.supports(tool) for adapter in cls._registry)

    @classmethod
    def wrap(cls, tool: Any) -> "ProviderTool | None":
        if not cls.supports(tool):
            return None
        return cls(tool)


@dataclass
class FunctionToolInfo:
    name: str
    description: str | None
    parameters: dict[str, object]


class RawFunctionDescription(TypedDict):
    name: str
    description: str | None
    parameters: dict[str, object]


@dataclass
class RawFunctionToolInfo:
    name: str
    raw_schema: dict[str, Any]


class _BaseFunctionTool(Tool, Generic[_InfoT, _P, _R]):

    def __init__(self, func: Callable[_P, _R], info: _InfoT, instance: Any = None) -> None:
        functools.update_wrapper(self, func)
        self._func = func
        self._info: _InfoT = info
        self._instance = instance

    @property
    def id(self) -> str:
        return self._info.name

    @property
    def info(self) -> _InfoT:
        return self._info

    def __get__(self, obj: Any, objtype: type | None = None) -> Self:
        if obj is None:
            return self

        # bind the tool to an instance
        bound_tool = self.__class__(self._func, self._info, instance=obj)
        sig = inspect.signature(self._func)

        params = list(sig.parameters.values())[1:]
        bound_tool.__signature__ = sig.replace(
            parameters=params)
        return bound_tool

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        if self._instance is not None:
            return self._func(self._instance, *args, **kwargs)
        return self._func(*args, **kwargs)


class FunctionTool(_BaseFunctionTool[FunctionToolInfo, _P, _R]):
    def __init__(
        self, func: Callable[_P, _R], info: FunctionToolInfo, instance: Any = None
    ) -> None:
        super().__init__(func, info, instance)
        setattr(self, "__tendo_tool_info", self._info)


class RawFunctionTool(_BaseFunctionTool[RawFunctionToolInfo, _P, _R]):

    def __init__(
        self, func: Callable[_P, _R], info: RawFunctionToolInfo, instance: Any = None
    ) -> None:
        super().__init__(func, info, instance)
        setattr(self, "__tendo_raw_tool_info", self._info)


@overload
def function_tool(
    f: Callable[_P, _R],
    *,
    raw_schema: RawFunctionDescription | dict[str, Any],
) -> RawFunctionTool[_P, _R]:
    ...


@overload
def function_tool(
    f: None = None,
    *,
    raw_schema: RawFunctionDescription | dict[str, Any],
) -> Callable[[Callable[_P, _R]], RawFunctionTool[_P, _R]]:
    ...


@overload
def function_tool(
    f: Callable[_P, _R],
    *,
    name: str | None = None,
    description: str | None = None,
) -> FunctionTool[_P, _R]:
    ...


@overload
def function_tool(
    f: None = None,
    *,
    name: str | None = None,
    description: str | None = None,
) -> Callable[[Callable[_P, _R]], FunctionTool[_P, _R]]:
    ...


def function_tool(
    f: Callable[_P, _R] | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    raw_schema: RawFunctionDescription | dict[str, Any] | None = None,
) -> (
    FunctionTool[_P, _R]
    | RawFunctionTool[_P, _R]
    | Callable[[Callable[_P, _R]], FunctionTool[_P, _R] | RawFunctionTool[_P, _R]]
):
    def deco_raw(
        func: Callable[_P, _R],
    ) -> RawFunctionTool[_P, _R]:
        assert raw_schema is not None

        if not raw_schema.get("name"):
            raise ValueError("raw function name cannot be empty")

        if "parameters" not in raw_schema:
            raise ValueError(
                "raw function description must contain a parameters key")

        schema = {**raw_schema}
        info = RawFunctionToolInfo(
            name=raw_schema["name"],
            raw_schema=schema
        )
        return RawFunctionTool(func, info)

    def deco_func(func: Callable[_P, _R]) -> FunctionTool[_P, _R]:
        from docstring_parser import parse_from_object

        wrapped: Callable[..., Any] = func

        docstring = parse_from_object(func)
        info = FunctionToolInfo(
            name=name or func.__name__,
            description=description or docstring.description,

        )
        return FunctionTool(wrapped, info)

    if f is not None:
        return deco_raw(f) if raw_schema is not None else deco_func(f)
    return deco_raw if raw_schema is not None else deco_func


def get_fnc_tool_names(tools: Sequence[Tool | Toolset]) -> list[str]:
    """Get names of all function and raw function tools in the list, unwrapping tool sets."""
    names = []
    for tool in tools:
        if isinstance(tool, (FunctionTool, RawFunctionTool)):
            names.append(tool.info.name)
        elif isinstance(tool, Toolset):
            names.extend(get_fnc_tool_names(tool.tools))

    return names


def _get_tool_description(tool: FunctionTool | RawFunctionTool) -> str:
    if isinstance(tool, FunctionTool):
        return tool.info.description or ""
    return str(tool.info.raw_schema.get("description", ""))


def _get_tool_params(tool: FunctionTool | RawFunctionTool) -> dict[str, str]:
    if isinstance(tool, FunctionTool):
        callable_fn = getattr(tool, "_func", None) or getattr(
            tool, "_tool", None)
        if callable_fn and hasattr(callable_fn, "__name__"):
            model = function_arguments_to_pydantic_model(callable_fn)
            return {name: field.description or "" for name, field in model.model_fields.items()}

        if hasattr(callable_fn, "args_schema") and callable_fn.args_schema:
            return {
                name: field.description or ""
                for name, field in callable_fn.args_schema.model_fields.items()
            }
        return {}

    props = tool.info.raw_schema.get("parameters", {}).get("properties", {})
    return {
        name: prop.get("description", "") if isinstance(prop, dict) else ""
        for name, prop in props.items()
    }


def _build_tool_schema(tool: FunctionTool | RawFunctionTool) -> dict[str, Any]:
    """Build a JSON-serializable tool schema with full parameter type info."""
    if isinstance(tool, FunctionTool):
        func = getattr(tool, "_func", None) or getattr(
            tool, "__wrapped__", None)
        if func and hasattr(func, "__name__"):
            model = function_arguments_to_pydantic_model(func)
            return {
                "name": tool.info.name,
                "description": tool.info.description or "",
                "parameters": model.model_json_schema(),
            }
        return {
            "name": tool.info.name,
            "description": tool.info.description or "",
            "parameters": {"type": "object", "properties": {}},
        }

    # RawFunctionTool — use raw_schema directly
    raw = tool.info.parameters
    return {
        "name": raw.get("name", tool.id),
        "description": raw.get("description", ""),
        "parameters": raw.get("parameters", {}),
    }


class Toolset:

    def __init__(self, *, id: str, tools: Sequence[Tool | Toolset] | None = None) -> None:
        self._id = id
        self._tools: Sequence[Tool | Toolset] = list(
            tools) if tools is not None else []

    @property
    def id(self) -> str:
        return self._id

    @property
    def tools(self) -> Sequence[Tool | Toolset]:
        return self._tools

    async def setup(self) -> Self:
        """Initialize the toolset and any nested toolsets."""
        toolsets = [tool for tool in self.tools if isinstance(tool, Toolset)]
        if toolsets:
            await asyncio.gather(*(toolset.setup() for toolset in toolsets))
        return self

    async def aclose(self) -> None:
        """Close the toolset and release any held resources"""
        toolsets = [tool for tool in self._tools if isinstance(tool, Toolset)]
        if toolsets:
            await asyncio.gather(*(toolset.aclose() for toolset in toolsets))


class ToolContext:
    """
    Lightweight tool registry.

    Responsible for:

    - Flattening nested Toolsets
    - Registering FunctionTools
    - Registering ProviderTools
    - Looking up FunctionTools by name
    """

    def __init__(
        self,
        tools: Sequence[Tool | Toolset] | None = None,
    ) -> None:
        self._tools: list[Tool | Toolset] = []

        self._function_tools: dict[
            str,
            FunctionTool | RawFunctionTool,
        ] = {}

        self._provider_tools: list[
            ProviderTool,
        ] = []

        self._toolsets: list[
            Toolset,
        ] = []
        self._provider_adapter = ProviderTool()
        self._provider_adapter.register_adapter(LangChainAdapter)

        if tools:
            self.register_many(
                tools,
            )

    @classmethod
    def empty(
        cls,
    ) -> "ToolContext":

        return cls()

    @classmethod
    def from_tools(
        cls,
        tools: Sequence[Tool | Toolset] | None,
    ) -> "ToolContext":

        context = cls()

        if tools:
            context.register_many(
                tools,
            )

        return context

    @property
    def tools(
        self,
    ) -> list[Tool]:

        return self.flatten()

    @property
    def function_tools(
        self,
    ) -> dict[str, FunctionTool | RawFunctionTool]:
        return self._function_tools

    @cached_property
    def proxy(
        self,
    ):

        from app.runtime.toolsets.tool_proxy import ToolProxyToolset

        return ToolProxyToolset(
            id="proxy",
            tools=self._tools,
        )

    @property
    def function_tools(
        self,
    ) -> dict[str, FunctionTool | RawFunctionTool]:

        return self._function_tools

    @property
    def provider_tools(
        self,
    ) -> list[ProviderTool]:

        return self._provider_tools

    @property
    def toolsets(
        self,
    ) -> list[Toolset]:

        return self._toolsets

    def is_empty(
        self,
    ) -> bool:

        return (
            not self._function_tools
            and not self._provider_tools
        )

    def flatten(
        self,
    ) -> list[Tool]:

        return [
            *self._function_tools.values(),
            *self._provider_tools,
        ]

    def get_function_tool(
        self,
        name: str,
    ) -> FunctionTool | RawFunctionTool | None:

        return self._function_tools.get(
            name,
        )

    def register(
        self,
        tool: Tool | Toolset,
    ) -> None:

        self._tools.append(
            tool,
        )

        self._register(
            tool,
        )

        self.__dict__.pop(
            "proxy",
            None,
        )

    def register_many(
        self,
        tools: Sequence[Tool | Toolset],
    ) -> None:

        for tool in tools:
            self.register(
                tool,
            )

    def update_tools(
        self,
        tools: Sequence[Tool | Toolset],
    ) -> None:

        self.clear()

        self.register_many(
            tools,
        )

    def clear(
        self,
    ) -> None:

        self._tools.clear()
        self._function_tools.clear()
        self._provider_tools.clear()
        self._toolsets.clear()

        self.__dict__.pop(
            "proxy",
            None,
        )

    def _register(
        self,
        tool: Tool | Toolset,
    ) -> None:
        """Recursively register tools."""

        # Nested Toolset
        if isinstance(tool, Toolset):
            self._toolsets.append(tool)
            for nested in tool.tools:
                self._register(nested)
            return

        # Provider Tool
        if isinstance(tool, ProviderTool):
            self._provider_tools.append(tool)
            return

        # Function Tool
        if isinstance(tool, (FunctionTool, RawFunctionTool)):
            existing = self._function_tools.get(tool.info.name)
            if existing is not None:
                if existing is tool:
                    return
                raise ValueError(
                    f"Duplicate function tool '{tool.info.name}'.")
            self._function_tools[tool.info.name] = tool
            return

        provider = self._provider_adapter.wrap(tool)

        if provider is not None:
            self._provider_tools.append(provider)
            return

        raise TypeError(f"Unsupported tool type: {type(tool)}")
