"""Dynamically infer tool schemas from callable definitions and registries."""

import inspect
from typing import get_type_hints


def tools_to_prompt(tools: list) -> str:
    """Generate a prompt-friendly description of available tools from LangChain tool definitions.
    
    Reads the tool name, docstring, and parameter annotations automatically.
    No manual editing needed — add a tool to the list and it appears in the prompt.
    """
    lines = []
    for tool in tools:
        name = tool.name
        description = tool.description or ""

        schema = tool.args_schema
        params = []
        if schema:
            for field_name, field_info in schema.model_fields.items():
                field_type = field_info.annotation.__name__ if hasattr(field_info.annotation, '__name__') else str(field_info.annotation)
                default = f" = {field_info.default!r}" if field_info.default is not None else ""
                params.append(f"{field_name}: {field_type}{default}")

        params_str = ", ".join(params)
        lines.append(f"- {name}({params_str})")
        lines.append(f"  {description}")
        lines.append("")

    return "\n".join(lines)


def registry_tools_to_prompt() -> str:
    """Infer tool schemas from the DB registry and generate a prompt-friendly description.

    Reads function signatures, type annotations, and docstrings from all registered tools.
    No manual editing needed — register a tool with @register and it appears here.
    """
    from app.db.registry import _registry

    if not _registry:
        import app.db.tools  # noqa: F401 — trigger auto-registration

    lines = []
    for name, fn in sorted(_registry.items()):
        doc = inspect.getdoc(fn) or ""
        sig = inspect.signature(fn)
        hints = get_type_hints(fn)

        params = []
        for param_name, param in sig.parameters.items():
            if param_name in ("kwargs", "self"):
                continue
            annotation = hints.get(param_name)
            type_str = annotation.__name__ if annotation and hasattr(annotation, "__name__") else str(annotation or "any")
            if param.default is inspect.Parameter.empty:
                params.append(f"{param_name}: {type_str} (required)")
            else:
                params.append(f"{param_name}: {type_str} = {param.default!r}")

        params_str = ", ".join(params)
        lines.append(f"- {name}({params_str})")
        if doc:
            lines.append(f"  {doc}")
        lines.append("")

    return "\n".join(lines)


def registry_tool_names() -> list[str]:
    """Return list of all registered DB tool names."""
    from app.db.registry import _registry

    if not _registry:
        import app.db.tools  # noqa: F401

    return sorted(_registry.keys())
