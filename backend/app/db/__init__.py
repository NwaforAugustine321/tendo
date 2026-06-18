"""Database module — Supabase client, tool registry, and DB operations."""

# Import tools to trigger @register decorators
import app.db.tools  # noqa: F401

from app.db.client import get_client
from app.db.node import execute_tool
from app.db.registry import get_tool, list_tools

__all__ = ["get_client", "execute_tool", "get_tool", "list_tools"]
