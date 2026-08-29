"""Agent spec loader — reads .md configuration files and assembles system prompts."""

from dataclasses import dataclass
from pathlib import Path

SPECS_DIR = Path(__file__).parent.parent / "agents" / "specs"
ASSEMBLY_ORDER = ["role", "backstory", "goal", "skill", "tools", "output"]

_cache: dict[str, "AgentConfig"] = {}


@dataclass
class AgentConfig:
    system_prompt: str
    agent_name: str
    has_tools: bool


def load(agent_name: str, tools: list = None) -> AgentConfig:
    """Load agent spec from .md files.
    
    Args:
        agent_name: Name/path of the agent spec directory.
        tools: Optional list of LangChain tools to inject via {TOOLS} placeholder.
    """
    from app.config.settings import settings

    cache_key = agent_name if not tools else None
    if not settings.spec_hot_reload and cache_key and cache_key in _cache:
        return _cache[cache_key]

    spec_dir = SPECS_DIR / agent_name
    if not spec_dir.is_dir():
        raise FileNotFoundError(f"No spec directory found for agent: {agent_name}")

    parts: list[str] = []
    has_tools = False

    for section in ASSEMBLY_ORDER:
        file = spec_dir / f"{section}.md"
        if file.exists():
            content = file.read_text(encoding="utf-8").strip()
            if content:
                parts.append(f"## {section.upper()}\n\n{content}")
            if section == "tools":
                has_tools = True

    if not parts:
        raise ValueError(f"Agent spec '{agent_name}' has no content in any .md file")

    system_prompt = "\n\n".join(parts)

    # Inject agent name
    system_prompt = system_prompt.replace("{AGENT_NAME}", settings.agent_name)

    # Inject tools passed from the node
    if tools and "{TOOLS}" in system_prompt:
        from app.lib.tool_schema import tools_schema_and_description
        system_prompt = system_prompt.replace("{TOOLS}", tools_schema_and_description(tools))

    config = AgentConfig(system_prompt=system_prompt, agent_name=agent_name, has_tools=has_tools)

    if not settings.spec_hot_reload and cache_key:
        _cache[cache_key] = config

    return config
