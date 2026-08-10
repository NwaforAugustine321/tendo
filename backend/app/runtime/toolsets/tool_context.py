from __future__ import annotations

import asyncio
import functools
import inspect
import json
import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from enum import Flag, auto
from functools import cached_property
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

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stub types for undefined external references
# ---------------------------------------------------------------------------

RunContext = Any
"""RunContext placeholder — replace with actual import when available."""

FunctionCall = Any
"""FunctionCall placeholder — replace with actual import when available."""


class ToolError(Exception):
    """Raised when a tool encounters an error that should be surfaced to the LLM."""

    pass


# ---------------------------------------------------------------------------
# Confirm-duplicate constants
# ---------------------------------------------------------------------------

CONFIRM_DUPLICATE_PARAM = "confirm_duplicate"
_CONFIRM_DUPLICATE_DESCRIPTION = (
    "Set to true to confirm you want to call this tool again even though a "
    "duplicate call is already in progress."
)

# ---------------------------------------------------------------------------
# Type variables
# ---------------------------------------------------------------------------

_T = TypeVar("_T")
_InfoT = TypeVar("_InfoT", bound=Any)
_P = ParamSpec("_P")
_R = TypeVar("_R", bound=Awaitable[Any])

# ---------------------------------------------------------------------------
# NotGiven sentinel
# ---------------------------------------------------------------------------


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


NotGivenOr: TypeAlias = _T | NotGiven  # type: ignore[type-arg]
NOT_GIVEN = NotGiven()


# ---------------------------------------------------------------------------
# Tool flag and base classes
# ---------------------------------------------------------------------------


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
    """Wraps an external provider tool for use in the toolset system.

    Supports multiple tool frameworks:
    - LangChain: @tool decorated functions (BaseTool instances)
    - CrewAI: CrewAI tool instances
    - Plain callables: Any function with name, description, and type hints
    - Dict schema: Raw tool definition as a dictionary

    Usage:
        ProviderTool(langchain_tool)
        ProviderTool(crewai_tool)
        ProviderTool(my_function, name="my_tool", description="Does something")
        ProviderTool.from_dict({"name": "my_tool", "description": "...", "func": fn, "parameters": {...}})
    """

    def __init__(
        self,
        tool: Any = None,
        *,
        name: str | None = None,
        description: str | None = None,
        parameters: dict | None = None,
        func: Any | None = None,
    ) -> None:
        self._tool = tool
        self._name = name
        self._description = description
        self._parameters = parameters
        self._func = func

        # Auto-detect tool framework
        if tool is not None:
            self._adapter = self._detect_adapter(tool)
        elif func is not None:
            self._adapter = "callable"
        else:
            raise ValueError(
                "ProviderTool requires either a tool object or a func callable")

    @classmethod
    def from_dict(cls, schema: dict) -> "ProviderTool":
        """Create a ProviderTool from a raw dictionary schema."""
        return cls(
            tool=None,
            name=schema.get("name"),
            description=schema.get("description", ""),
            parameters=schema.get("parameters"),
            func=schema.get("func"),
        )

    def _detect_adapter(self, tool: Any) -> str:
        """Detect which framework the tool belongs to."""
        # LangChain
        try:
            from langchain_core.tools import BaseTool
            if isinstance(tool, BaseTool):
                return "langchain"
        except ImportError:
            pass

        # CrewAI
        try:
            from crewai.tools import BaseTool as CrewBaseTool
            if isinstance(tool, CrewBaseTool):
                return "crewai"
        except ImportError:
            pass

        # Plain callable
        if callable(tool):
            return "callable"

        raise TypeError(f"Unsupported tool type: {type(tool)}")

    @property
    def id(self) -> str:
        return self.name

    @property
    def name(self) -> str:
        if self._name:
            return self._name
        if self._adapter == "langchain":
            return self._tool.name
        if self._adapter == "crewai":
            return self._tool.name
        if self._adapter == "callable":
            fn = self._tool or self._func
            return getattr(fn, "__name__", "unknown_tool")
        return "unknown_tool"

    @property
    def description(self) -> str:
        if self._description:
            return self._description
        if self._adapter == "langchain":
            return self._tool.description or ""
        if self._adapter == "crewai":
            return self._tool.description or ""
        if self._adapter == "callable":
            fn = self._tool or self._func
            return getattr(fn, "__doc__", "") or ""
        return ""

    @property
    def args_schema(self):
        """Return a Pydantic model describing the tool's parameters."""
        if self._parameters:
            # Build a model from raw parameters dict
            from pydantic import create_model, Field as PydanticField
            fields = {}
            props = self._parameters.get("properties", {})
            required = self._parameters.get("required", [])
            for p_name, p_info in props.items():
                p_type = str  # default
                if p_info.get("type") == "integer":
                    p_type = int
                elif p_info.get("type") == "number":
                    p_type = float
                elif p_info.get("type") == "boolean":
                    p_type = bool
                elif p_info.get("type") == "object":
                    p_type = dict
                elif p_info.get("type") == "array":
                    p_type = list
                default = ... if p_name in required else None
                fields[p_name] = (p_type, PydanticField(
                    default=default, description=p_info.get("description", "")))
            return create_model(f"{self.name}_Args", **fields)

        if self._adapter == "langchain":
            return getattr(self._tool, "args_schema", None)
        if self._adapter == "crewai":
            return getattr(self._tool, "args_schema", None)
        if self._adapter == "callable":
            fn = self._tool or self._func
            if hasattr(fn, "__name__"):
                from app.toolsets.utils import function_arguments_to_pydantic_model
                try:
                    return function_arguments_to_pydantic_model(fn)
                except Exception:
                    pass
        return None

    def invoke(self, arguments: dict) -> Any:
        """Synchronous invocation."""
        if self._adapter == "langchain":
            return self._tool.invoke(arguments)
        if self._adapter == "crewai":
            return self._tool._run(**arguments)
        if self._adapter == "callable":
            fn = self._tool or self._func
            return fn(**arguments)
        raise NotImplementedError(
            f"invoke not supported for adapter: {self._adapter}")

    async def ainvoke(self, arguments: dict) -> Any:
        """Async invocation."""
        if self._adapter == "langchain":
            return await self._tool.ainvoke(arguments)
        if self._adapter == "crewai":
            # CrewAI tools are typically sync
            return self._tool._run(**arguments)
        if self._adapter == "callable":
            fn = self._tool or self._func
            import asyncio
            if asyncio.iscoroutinefunction(fn):
                return await fn(**arguments)
            return fn(**arguments)
        raise NotImplementedError(
            f"ainvoke not supported for adapter: {self._adapter}")


# ---------------------------------------------------------------------------
# Duplicate mode / scope
# ---------------------------------------------------------------------------

DuplicateMode = Literal["allow", "reject", "replace", "confirm"]

DuplicateScope = Literal["name", "name_and_args"]
"""What counts as a duplicate of an in-flight call, i.e. what ``on_duplicate`` acts on.

``"name"``           any in-flight call of the same tool (default).
``"name_and_args"``  same tool *and* same arguments, so concurrent calls of one
                     tool with different arguments are not duplicates::

                         @function_tool(on_duplicate="reject", duplicate_scope="name_and_args")
                         async def check_order(ctx: RunContext, order_id: str) -> str: ...

                     Arguments are compared *after* validation, so a parameter the
                     LLM omitted on one call and passed explicitly on the next still
                     reads as the same call, and ``1`` matches ``1.0`` for a ``float``
                     parameter. Raw function tools (including MCP tools) have no
                     per-parameter schema, so their arguments are compared as sent.

                     Comparison fails open — an unrepresentable argument or a
                     validation error leaves the call treated as sent rather than
                     blocking it — so don't rely on this as an exactly-once
                     guarantee; put that in the tool body.
"""


# ---------------------------------------------------------------------------
# FunctionToolInfo / RawFunctionToolInfo
# ---------------------------------------------------------------------------


@dataclass
class FunctionToolInfo:
    name: str
    description: str | None
    flags: ToolFlag
    on_duplicate: DuplicateMode = "allow"
    duplicate_scope: DuplicateScope = "name"


class RawFunctionDescription(TypedDict):
    """
    Represents the raw function schema format used in LLM function calling APIs.

    This structure directly maps to OpenAI's function definition format as documented at:
    https://platform.openai.com/docs/guides/function-calling?api-mode=responses

    It is also compatible with other LLM providers that support raw JSON Schema-based
    function definitions.
    """

    name: str
    description: NotRequired[str | None]
    parameters: dict[str, object]


@dataclass
class RawFunctionToolInfo:
    name: str
    raw_schema: dict[str, Any]
    flags: ToolFlag
    on_duplicate: DuplicateMode = "allow"
    duplicate_scope: DuplicateScope = "name"


# ---------------------------------------------------------------------------
# _BaseFunctionTool / FunctionTool / RawFunctionTool
# ---------------------------------------------------------------------------


class _BaseFunctionTool(Tool, Generic[_InfoT, _P, _R]):
    """Base class for function tool wrappers with descriptor support."""

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
        # skip the instance parameter (e.g. usually the 'self')
        params = list(sig.parameters.values())[1:]
        bound_tool.__signature__ = sig.replace(
            parameters=params)  # type: ignore[attr-defined]
        return bound_tool

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        if self._instance is not None:
            return self._func(self._instance, *args, **kwargs)
        return self._func(*args, **kwargs)


class FunctionTool(_BaseFunctionTool[FunctionToolInfo, _P, _R]):
    """Wrapper for a function decorated with @function_tool"""

    def __init__(
        self, func: Callable[_P, _R], info: FunctionToolInfo, instance: Any = None
    ) -> None:
        super().__init__(func, info, instance)
        setattr(self, "__livekit_tool_info", self._info)


class RawFunctionTool(_BaseFunctionTool[RawFunctionToolInfo, _P, _R]):
    """Wrapper for a function decorated with @function_tool(raw_schema=...)"""

    def __init__(
        self, func: Callable[_P, _R], info: RawFunctionToolInfo, instance: Any = None
    ) -> None:
        super().__init__(func, info, instance)
        setattr(self, "__livekit_raw_tool_info", self._info)


# ---------------------------------------------------------------------------
# function_tool decorator (overloads + implementation)
# ---------------------------------------------------------------------------


@overload
def function_tool(
    f: Callable[_P, _R],
    *,
    raw_schema: RawFunctionDescription | dict[str, Any],
    flags: ToolFlag = ToolFlag.NONE,
    on_duplicate: DuplicateMode = "allow",
    duplicate_scope: DuplicateScope = "name",
) -> RawFunctionTool[_P, _R]:
    ...


@overload
def function_tool(
    f: None = None,
    *,
    raw_schema: RawFunctionDescription | dict[str, Any],
    flags: ToolFlag = ToolFlag.NONE,
    on_duplicate: DuplicateMode = "allow",
    duplicate_scope: DuplicateScope = "name",
) -> Callable[[Callable[_P, _R]], RawFunctionTool[_P, _R]]:
    ...


@overload
def function_tool(
    f: Callable[_P, _R],
    *,
    name: str | None = None,
    description: str | None = None,
    flags: ToolFlag = ToolFlag.NONE,
    on_duplicate: DuplicateMode = "allow",
    duplicate_scope: DuplicateScope = "name",
) -> FunctionTool[_P, _R]:
    ...


@overload
def function_tool(
    f: None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    flags: ToolFlag = ToolFlag.NONE,
    on_duplicate: DuplicateMode = "allow",
    duplicate_scope: DuplicateScope = "name",
) -> Callable[[Callable[_P, _R]], FunctionTool[_P, _R]]:
    ...


def function_tool(
    f: Callable[_P, _R] | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    raw_schema: RawFunctionDescription | dict[str, Any] | None = None,
    flags: ToolFlag = ToolFlag.NONE,
    on_duplicate: DuplicateMode = "allow",
    duplicate_scope: DuplicateScope = "name",
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
        if on_duplicate == "confirm":
            schema["parameters"] = _inject_confirm_duplicate(
                schema["parameters"])

        info = RawFunctionToolInfo(
            name=raw_schema["name"],
            raw_schema=schema,
            flags=flags,
            on_duplicate=on_duplicate,
            duplicate_scope=duplicate_scope,
        )
        return RawFunctionTool(func, info)

    def deco_func(func: Callable[_P, _R]) -> FunctionTool[_P, _R]:
        from docstring_parser import parse_from_object

        wrapped: Callable[..., Any] = func
        if on_duplicate == "confirm":
            wrapped = _wrap_with_confirm_duplicate(func)

        docstring = parse_from_object(func)
        info = FunctionToolInfo(
            name=name or func.__name__,
            description=description or docstring.description,
            flags=flags,
            on_duplicate=on_duplicate,
            duplicate_scope=duplicate_scope,
        )
        return FunctionTool(wrapped, info)

    if f is not None:
        return deco_raw(f) if raw_schema is not None else deco_func(f)
    return deco_raw if raw_schema is not None else deco_func


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _wrap_with_confirm_duplicate(func: Callable[..., Any]) -> Callable[..., Any]:
    """Extend ``func``'s signature with a CONFIRM_DUPLICATE_PARAM kwarg, stripped
    by the wrapper before delegating so direct calls with the original args still work."""
    try:
        resolved = get_type_hints(func, include_extras=True)
    except Exception:
        resolved = dict(getattr(func, "__annotations__", {}))

    annotation = Annotated[
        bool | None, Field(
            default=False, description=_CONFIRM_DUPLICATE_DESCRIPTION)
    ]
    new_annotations = {**resolved, CONFIRM_DUPLICATE_PARAM: annotation}

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        kwargs.pop(CONFIRM_DUPLICATE_PARAM, None)
        result = func(*args, **kwargs)
        if asyncio.iscoroutine(result):
            return await result
        return result

    sig = inspect.signature(func)
    extra = inspect.Parameter(
        CONFIRM_DUPLICATE_PARAM,
        inspect.Parameter.KEYWORD_ONLY,
        default=False,
        annotation=annotation,
    )
    wrapper.__signature__ = sig.replace(
        # type: ignore[attr-defined]
        parameters=[*sig.parameters.values(), extra])
    # set both for PEP 649: __annotations__ for 3.10-3.13, __annotate__ for 3.14.
    # __annotate__ must come last — assigning __annotations__ nulls it on 3.14.
    wrapper.__annotations__ = new_annotations
    wrapper.__annotate__ = lambda _format=1: dict(
        new_annotations)  # type: ignore[attr-defined]
    return wrapper


def _inject_confirm_duplicate(parameters: dict[str, Any]) -> dict[str, Any]:
    """Add CONFIRM_DUPLICATE_PARAM to a raw JSON-schema (strict-mode conformant)."""
    params = {**parameters}
    properties = {**params.get("properties", {})}
    properties[CONFIRM_DUPLICATE_PARAM] = {
        "type": ["boolean", "null"],
        "description": _CONFIRM_DUPLICATE_DESCRIPTION,
    }
    params["properties"] = properties
    required = list(params.get("required", []))
    if CONFIRM_DUPLICATE_PARAM not in required:
        required.append(CONFIRM_DUPLICATE_PARAM)
    params["required"] = required
    return params


def is_function_tool(f: Any) -> TypeGuard[FunctionTool]:
    return isinstance(f, FunctionTool)


def get_function_info(f: FunctionTool) -> FunctionToolInfo:
    return f.info


def is_raw_function_tool(f: Any) -> TypeGuard[RawFunctionTool]:
    return isinstance(f, RawFunctionTool)


def get_raw_function_info(f: RawFunctionTool) -> RawFunctionToolInfo:
    return f.info


def _resolve_wrapped_tool(tool: Any) -> FunctionTool | RawFunctionTool | None:
    """Convert a wrapped tool to a FunctionTool or RawFunctionTool with a warning."""
    if not callable(tool):
        return None

    if isinstance(tool, (FunctionTool, RawFunctionTool)):
        return tool

    resolved_tool: FunctionTool | RawFunctionTool | None = None
    if (
        hasattr(tool, "__wrapped__")  # automatically added by functools.wraps
        and isinstance(tool.__wrapped__, (FunctionTool, RawFunctionTool))
    ):
        wrapped = tool.__wrapped__
        resolved_tool = wrapped.__class__(tool, wrapped.info)  # type: ignore

    elif (info := getattr(tool, "__livekit_tool_info", None)) and isinstance(
        info, FunctionToolInfo
    ):
        resolved_tool = FunctionTool(tool, info)

    elif (info := getattr(tool, "__livekit_raw_tool_info", None)) and isinstance(
        info, RawFunctionToolInfo
    ):
        resolved_tool = RawFunctionTool(tool, info)

    if resolved_tool:
        tool_name = resolved_tool.info.name
        logger.warning(
            f"function tool {tool_name} is wrapped, this may cause unexpected behavior and not be supported in future versions, "
            "please wrap the original function before converting to a function tool.",
            extra={
                "function_tool": tool_name,
            },
        )

    return resolved_tool


def find_function_tools(cls_or_obj: Any) -> list[FunctionTool | RawFunctionTool]:
    methods: list[FunctionTool | RawFunctionTool] = []
    for _, member in inspect.getmembers(cls_or_obj):
        if isinstance(member, (FunctionTool, RawFunctionTool)):
            methods.append(member)
        elif normalized_tool := _resolve_wrapped_tool(member):
            methods.append(normalized_tool)

    return methods


def get_fnc_tool_names(tools: Sequence[Tool | Toolset]) -> list[str]:
    """Get names of all function and raw function tools in the list, unwrapping tool sets."""
    names = []
    for tool in tools:
        if isinstance(tool, (FunctionTool, RawFunctionTool)):
            names.append(tool.info.name)
        elif isinstance(tool, Toolset):
            names.extend(get_fnc_tool_names(tool.tools))

    return names


# ---------------------------------------------------------------------------
# Toolset
# ---------------------------------------------------------------------------


class Toolset:
    @dataclass
    class ToolCalledEvent:
        ctx: RunContext
        arguments: dict[str, Any]

    @dataclass
    class ToolCompletedEvent:
        ctx: RunContext
        output: Any | Exception | None

    def __init__(self, *, id: str, tools: Sequence[Tool | Toolset] | None = None) -> None:
        self._id = id
        self._tools: Sequence[Tool | Toolset] = list(
            tools) if tools is not None else []
        self._tools.extend(find_function_tools(self))

    @property
    def id(self) -> str:
        return self._id

    @property
    def tools(self) -> Sequence[Tool | Toolset]:
        return self._tools

    async def setup(self) -> Self:
        """Initialize the toolset and any nested toolsets.

        Called automatically by ``AgentActivity`` when an agent starts.
        """
        toolsets = [tool for tool in self.tools if isinstance(tool, Toolset)]
        if toolsets:
            await asyncio.gather(*(toolset.setup() for toolset in toolsets))
        return self

    async def aclose(self) -> None:
        """Close the toolset and release any held resources.

        Agent-scoped toolsets (passed to ``Agent(tools=...)``) are closed when the
        ``AgentActivity`` ends (on agent transition or session close). Session-scoped
        toolsets (passed to ``AgentSession(tools=...)``) are closed only when the
        ``AgentSession`` shuts down.
        """
        toolsets = [tool for tool in self._tools if isinstance(tool, Toolset)]
        if toolsets:
            await asyncio.gather(*(toolset.aclose() for toolset in toolsets))


# ---------------------------------------------------------------------------
# SearchItem / SearchStrategy / KeywordSearchStrategy / BM25SearchStrategy
# (extracted to app.toolsets.strategy — re-exported here for compatibility)
# ---------------------------------------------------------------------------

from app.toolsets.strategy import (  # noqa: E402
    BM25SearchStrategy,
    KeywordSearchStrategy,
    SearchItem,
    SearchStrategy,
)


# ---------------------------------------------------------------------------
# Tool schema helpers
# ---------------------------------------------------------------------------


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
    raw = tool.info.raw_schema
    return {
        "name": raw.get("name", tool.id),
        "description": raw.get("description", ""),
        "parameters": raw.get("parameters", {}),
    }


# ---------------------------------------------------------------------------
# Utility functions (imported from utils.py)
# ---------------------------------------------------------------------------

from app.toolsets.utils import (  # noqa: E402
    function_arguments_to_pydantic_model,
    is_context_type,
    parse_function_arguments,
    prepare_function_arguments,
)


# ---------------------------------------------------------------------------
# ToolContext
# ---------------------------------------------------------------------------


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

        if isinstance(
            tool,
            Toolset,
        ):

            self._toolsets.append(
                tool,
            )

            for nested in tool.tools:
                self._register(
                    nested,
                )

            return

        if isinstance(
            tool,
            ProviderTool,
        ):

            self._provider_tools.append(
                tool,
            )

            return

        if isinstance(
            tool,
            (
                FunctionTool,
                RawFunctionTool,
            ),
        ):

            existing = self._function_tools.get(
                tool.info.name,
            )

            if (
                existing is not None
                and existing is not tool
            ):
                raise ValueError(
                    f"Duplicate function tool '{tool.info.name}'."
                )

            self._function_tools[
                tool.info.name
            ] = tool

            return

        # Wrap any callable or third-party tool (e.g. LangChain StructuredTool)
        # as a ProviderTool so it can be registered.
        if callable(tool) or hasattr(tool, "invoke"):
            provider = ProviderTool(tool)
            self._provider_tools.append(provider)
            return

        raise TypeError(
            f"Unsupported tool type: {type(tool)}"
        )
