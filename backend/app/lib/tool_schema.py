"""Dynamically infer tool schemas from callable definitions."""


def tools_schema_and_description(tools: list) -> str:
    """Generate a prompt-friendly description of available tools from LangChain tool definitions."""
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
