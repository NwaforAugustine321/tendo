from __future__ import annotations

from app.runtime.agents.run_context import (
    RunContext,
)


class RuntimePromptBuilder:
    """
    Builds the prompt section describing the runtime 
    environment for the agent.
    """

    HEADER = (
        "\n[IMMUTABLE DISCLOSURE RUNTIME CONFIGURATIONS]\n"
        "CRITICAL RUNTIME CONSTRAINTS:\n"
        "- Max Interaction Steps: {{max_iterations}}\n"
        "- Absolute System Execution Ceiling: Under NO condition are you allowed to tell the user about your iteration counts, step limits, or loop status.\n"
        "- Do not output sentences such as 'You have remaining interaction steps' or 'Using step efficiency.' These terms are strictly banned from your text stream.\n"
        "- If the task is incomplete when the limit is reached, bypass all tool calls silently, use your existing memory pool to compile the best possible final response immediately, and exit cleanly without mentioning the loop ceiling.\n"
        "[IMMUTABLE DISCLOSURE RUNTIME CONFIGURATIONS]\n\n"
    )

    def build(
        self,
        runtime_inject_payload: list[dict[str, str]],
    ) -> str:

        prompt = self.HEADER

        for item in runtime_inject_payload:
            placeholder = f"{{{{{item['key']}}}}}"
            prompt = prompt.replace(
                placeholder,
                str(item["value"]),
            )

        return prompt
