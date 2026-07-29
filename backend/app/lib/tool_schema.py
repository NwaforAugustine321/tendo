from __future__ import annotations

from enum import Enum
from types import UnionType
from typing import Any, Literal, TypedDict, get_args, get_origin

from pydantic import BaseModel
from pydantic_core import PydanticUndefined


def _type_name(tp: Any) -> str:
    """Pretty-print any typing annotation."""
    origin = get_origin(tp)

    if origin is None:
        if tp is Any:
            return "Any"

        if tp is type(None):
            return "None"

        if isinstance(tp, type):
            return tp.__name__

        return str(tp)

    if origin in (list,):
        return f"list[{_type_name(get_args(tp)[0])}]"

    if origin in (set,):
        return f"set[{_type_name(get_args(tp)[0])}]"

    if origin in (tuple,):
        return f"tuple[{', '.join(_type_name(a) for a in get_args(tp))}]"

    if origin in (dict,):
        k, v = get_args(tp)
        return f"dict[{_type_name(k)}, {_type_name(v)}]"

    if origin in (UnionType, getattr(__import__("typing"), "Union")):
        return " | ".join(_type_name(a) for a in get_args(tp))

    if origin is Literal:
        return "Literal[" + ", ".join(repr(x) for x in get_args(tp)) + "]"

    return str(tp)


def _walk_type(
    tp: Any,
    indent: str,
    lines: list[str],
    visited: set[type],
):
    """
    Recursively expand any nested typing annotation.
    """

    origin = get_origin(tp)


    if isinstance(tp, type) and issubclass(tp, BaseModel):

        if tp in visited:
            lines.append(f"{indent}<recursive {tp.__name__}>")
            return

        visited.add(tp)

        lines.append(f"{indent}{tp.__name__}")

        for name, field in tp.model_fields.items():

            required = field.is_required()

            default = ""
            if (
                not required
                and field.default is not PydanticUndefined
            ):
                default = f" = {field.default!r}"

            description = ""
            if field.description:
                description = f" - {field.description}"

            lines.append(
                f"{indent}  • {name}: {_type_name(field.annotation)}"
                f"{' [required]' if required else ''}"
                f"{default}"
                f"{description}"
            )

            _walk_type(
                field.annotation,
                indent + "      ",
                lines,
                visited,
            )

        return

  
    if origin in (list, set):
        args = get_args(tp)
        if args:
            _walk_type(args[0], indent, lines, visited)
        return


    if origin is tuple:
        for arg in get_args(tp):
            _walk_type(arg, indent, lines, visited)
        return


    if origin is dict:
        key, value = get_args(tp)

        lines.append(f"{indent}Key:")
        _walk_type(key, indent + "  ", lines, visited)

        lines.append(f"{indent}Value:")
        _walk_type(value, indent + "  ", lines, visited)

        return


    if origin in (UnionType, getattr(__import__("typing"), "Union")):
        for arg in get_args(tp):
            _walk_type(arg, indent, lines, visited)
        return


    if (
        isinstance(tp, type)
        and issubclass(tp, dict)
        and hasattr(tp, "__annotations__")
    ):
        lines.append(f"{indent}{tp.__name__}")

        for k, v in tp.__annotations__.items():
            lines.append(
                f"{indent}  • {k}: {_type_name(v)}"
            )
            _walk_type(v, indent + "      ", lines, visited)

        return


    if isinstance(tp, type) and issubclass(tp, Enum):
        values = ", ".join(repr(e.value) for e in tp)
        lines.append(f"{indent}Enum[{values}]")
        return


def tools_schema_and_description(tools: list) -> str:

    lines = []

    for tool in tools:

        lines.append(f"- {tool.name}")

        if tool.args_schema:

            lines.append("  Parameters:")

            for name, field in tool.args_schema.model_fields.items():

                required = field.is_required()

                default = ""
                if (
                    not required
                    and field.default is not PydanticUndefined
                ):
                    default = f" = {field.default!r}"

                description = ""
                if field.description:
                    description = f" - {field.description}"

                lines.append(
                    f"    • {name}: {_type_name(field.annotation)}"
                    f"{' [required]' if required else ''}"
                    f"{default}"
                    f"{description}"
                )

                _walk_type(
                    field.annotation,
                    "        ",
                    lines,
                    set(),
                )

        lines.append(f"  Description: {tool.description}")
        lines.append("")

    return "\n".join(lines)