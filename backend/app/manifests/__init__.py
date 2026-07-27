"""Manifest system for the AI OS architecture.

Manifests are stored as markdown files in the `data/` directory.
The Planner reads these files directly to discover available agents,
skills, tools, and knowledge collections — no Python registry layer.

Usage:
    from app.manifests import load_manifest

    agents_md = load_manifest("agents")
    tools_md = load_manifest("tools")
"""

from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"


def load_manifest(name: str) -> str:
    """Load a manifest markdown file by name.

    Args:
        name: The manifest name (without extension).
              One of: "agents", "skills", "tools", "knowledge"

    Returns:
        The full text content of the markdown file.

    Raises:
        FileNotFoundError: If the manifest file does not exist.
    """
    path = _DATA_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def list_manifests() -> list[str]:
    """Return the names of all available manifests."""
    return [p.stem for p in _DATA_DIR.glob("*.md")]
