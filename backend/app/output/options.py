"""Structured options output formatting."""


def format_options(
    option_type: str,
    prompt: str,
    options: list[dict],
    allows_freeform: bool = True,
) -> dict:
    """Format a structured-options response."""
    return {
        "mode": "structured_options",
        "option_type": option_type,
        "prompt": prompt,
        "options": options[:10],
        "allows_freeform": allows_freeform,
    }
