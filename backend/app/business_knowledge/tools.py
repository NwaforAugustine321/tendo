from app.memory.tools import get_business_memory_tools

# Re-export for backward compatibility — callers should pass business_id
INTELLIGENCE_TOOLS = get_business_memory_tools
