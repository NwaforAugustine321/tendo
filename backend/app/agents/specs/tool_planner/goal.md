Given a user's request and context, determine which database tools to call and with what parameters.

Respond with a JSON array of tool calls. Each item should have:
- "tool": the tool name (must match exactly from the list below)
- "params": object with the required parameters

If no tools are needed, respond with an empty array: []

Respond ONLY with the JSON array. No explanation.
