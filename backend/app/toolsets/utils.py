"""Argument parsing and pydantic model generation utilities for toolsets."""
from __future__ import annotations

import inspect
import json
import logging
import re
from collections.abc import Callable
from typing import (
    Annotated,
    Any,
    get_args,
    get_origin,
    get_type_hints,
)

import json_repair
import pydantic
from pydantic import BaseModel, create_model
from pydantic.fields import Field, FieldInfo
from pydantic_core import PydanticUndefined, from_json

logger = logging.getLogger(__name__)


def is_context_type(type_hint: Any, allow_subclasses: bool = False) -> bool:
    """Check if a type hint is a context type that should be excluded from tool params."""
    # No context types in this project — always return False
    return False


def function_arguments_to_pydantic_model(func: Callable[..., Any]) -> type[BaseModel]:
    """Create a Pydantic model from a function's signature. (excluding context types)"""

    from docstring_parser import parse_from_object

    fnc_names = func.__name__.split("_")
    fnc_name = "".join(x.capitalize() for x in fnc_names)
    model_name = fnc_name + "Args"

    docstring = parse_from_object(func)
    param_docs = {p.arg_name: p.description for p in docstring.params}

    signature = inspect.signature(func)
    type_hints = get_type_hints(func, include_extras=True)

    # field_name -> (type, FieldInfo or default)
    fields: dict[str, Any] = {}

    for param_name, param in signature.parameters.items():
        type_hint = type_hints[param_name]

        if is_context_type(type_hint, allow_subclasses=True):
            continue

        default_value = param.default if param.default is not param.empty else ...
        field_info: FieldInfo | None = None
        field_attrs: dict[str, Any] = {}

        # Annotated[str, Field(description="...")]
        if get_origin(type_hint) is Annotated:
            annotated_args = get_args(type_hint)
            type_hint = annotated_args[0]
            annotated_field = next(
                (x for x in annotated_args[1:] if isinstance(x, FieldInfo)), None
            )
            if annotated_field and hasattr(annotated_field, "asdict"):
                field_dict = annotated_field.asdict()
                field_attrs = field_dict["attributes"]
                if field_dict["metadata"]:
                    type_hint = Annotated[(type_hint, *field_dict["metadata"])]
            elif annotated_field:
                field_attrs["default"] = annotated_field.default
                field_attrs["description"] = annotated_field.description
                field_info = annotated_field

        if (
            default_value is not ...
            and field_attrs.get("default", PydanticUndefined) is PydanticUndefined
        ):
            field_attrs["default"] = default_value

        if field_attrs.get("description") is None:
            field_attrs["description"] = param_docs.get(param_name, None)

        if not field_info:
            field_info = Field(**field_attrs)
        else:
            for k, v in field_attrs.items():
                setattr(field_info, k, v)

        fields[param_name] = (type_hint, field_info)

    return create_model(model_name, **fields)


def parse_function_arguments(json_arguments: str) -> dict[str, Any]:
    """Parse a raw JSON tool-call arguments string into a dict."""
    try:
        args_dict: Any = from_json(json_arguments)
    except ValueError as strict_err:
        repaired = json_repair.loads(json_arguments)
        if repaired == "":
            raise ValueError(
                f"could not parse function arguments as JSON: {strict_err}: {json_arguments[:200]}"
            ) from strict_err
        cleaned = _strip_template_tokens(repaired)
        logger.warning(
            "repaired malformed function-call JSON arguments",
            extra={
                "raw_arguments": json_arguments[:500],
                "repaired": cleaned,
                "error": str(strict_err),
            },
        )
        args_dict = cleaned

    while isinstance(args_dict, str):
        try:
            args_dict = from_json(args_dict)
        except Exception:
            raise ValueError(
                f"function arguments decoded to a non-JSON string: {args_dict[:200]}"
            ) from None

    if args_dict is None:
        return {}
    if not isinstance(args_dict, dict):
        raise ValueError(
            f"expected dict from function arguments, "
            f"got {type(args_dict).__name__}: {json_arguments[:200]}"
        )
    return args_dict


def prepare_function_arguments(
    *,
    fnc,
    json_arguments: str | dict[str, Any],
    call_ctx=None,
    fnc_call=None,
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    """Create the positional and keyword arguments to call a function tool."""
    from app.toolsets.tool_context import ToolError

    if isinstance(json_arguments, dict):
        args_dict = json_arguments
    else:
        try:
            args_dict = parse_function_arguments(json_arguments)
        except ValueError as e:
            logger.error(
                f"error parsing arguments for `{fnc.info.name}`",
                extra={"function": fnc.info.name, "arguments": json_arguments},
            )
            raise ToolError(f"Error parsing arguments for `{fnc.info.name}`: {e}") from e

        if fnc_call is not None:
            canonical = json.dumps(args_dict, default=str)
            if canonical != json_arguments:
                fnc_call.arguments = canonical

    try:
        return _prepare_function_arguments(fnc=fnc, args_dict=args_dict, call_ctx=call_ctx)
    except Exception as e:
        if hasattr(e, '__class__') and e.__class__.__name__ == 'ToolError':
            raise
        if isinstance(e, (pydantic.ValidationError, ValueError, TypeError)):
            logger.error(
                f"error parsing arguments for `{fnc.info.name}`",
                extra={"function": fnc.info.name, "arguments": json_arguments},
            )
            raise ToolError(f"Error parsing arguments for `{fnc.info.name}`: {e}") from e
        logger.exception(
            f"error parsing arguments for `{fnc.info.name}`",
            extra={"function": fnc.info.name, "arguments": json_arguments},
        )
        raise


def _strip_template_tokens(value: Any) -> Any:
    """Strip leaked chat-template tokens from repaired JSON values."""
    if isinstance(value, str):
        return re.sub(r"<\|[^|]*\|>", "", value).strip()
    if isinstance(value, dict):
        return {k: _strip_template_tokens(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_strip_template_tokens(item) for item in value]
    return value


def _prepare_function_arguments(
    *,
    fnc,
    args_dict: dict[str, Any],
    call_ctx=None,
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    """Validate and bind parsed arguments to the function's signature."""
    from app.toolsets.tool_context import RawFunctionTool

    if isinstance(fnc, RawFunctionTool):
        if call_ctx is not None:
            return (args_dict,), {}
        return (args_dict,), {}

    model_cls = function_arguments_to_pydantic_model(fnc._func)
    validated = model_cls.model_validate(args_dict)
    kwargs = validated.model_dump()

    sig = inspect.signature(fnc._func)
    params = list(sig.parameters.keys())

    args: tuple[Any, ...] = ()
    if call_ctx is not None and params:
        first_param = params[0]
        type_hints = get_type_hints(fnc._func, include_extras=True)
        first_hint = type_hints.get(first_param)
        if first_hint is not None and first_param not in kwargs:
            args = (call_ctx,)

    return args, kwargs
