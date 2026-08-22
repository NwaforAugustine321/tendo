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
        "\n<runtime_configurations>\n"
        "This is the runtime configuration throughout the task.\n"
        "Max Interaction Steps: {{max_iterations}}\n"
        "Do not exceed the maximum steps. If the task is incomplete when the limit is reached, "
        "provide the best final response and exit."
        "</runtime_configurations>"

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
