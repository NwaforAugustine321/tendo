## Available Tools

Tool schemas are injected dynamically at runtime from the DB registry.
You will see a complete list of tools with their parameters in the "Available DB Tools" section of your system prompt.

Each tool has:
- A name (use this exactly in the "tool" field)
- Parameters with types and required/optional markers
- A description of what it does

business_id is auto-injected — only include it explicitly if targeting a different business.

## Parallel Tool Calls

You can call MULTIPLE memory tools in a single response — they execute in parallel.
Example: call get_profile AND search_memory at the same time to gather context before planning DB operations.
