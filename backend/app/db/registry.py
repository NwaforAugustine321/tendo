"""Tool registry — maps tool names to their handler functions."""

from typing import Any, Callable

_registry: dict[str, Callable[..., Any]] = {}


def register(name: str):
    """Decorator to register a DB tool."""
    def wrapper(fn: Callable[..., Any]):
        _registry[name] = fn
        return fn
    return wrapper


def get_tool(name: str) -> Callable[..., Any] | None:
    return _registry.get(name)


def list_tools() -> list[str]:
    return list(_registry.keys())
