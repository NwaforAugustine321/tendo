from __future__ import annotations

import json

from pydantic import BaseModel


class OutputFormatter:
    """
    Builds the output formatting instructions for the LLM.

    When an output schema is provided, the model is instructed
    to return JSON conforming to that schema.
    """

    def build(
        self,
        output_type: type[BaseModel] | None = None,
    ) -> str:

        if output_type is None:
            return ""

        schema = json.dumps(
            output_type.model_json_schema(),
            indent=2,
        )

        return "\n".join(
            [
                "## Output Format",
                "",
                "Return ONLY a valid JSON object.",
                "",
                "The JSON MUST conform exactly to the following schema:",
                "",
                schema,
                "",
                "Rules:",
                "- Do not return Markdown.",
                "- Do not wrap the JSON in code fences.",
                "- Do not include explanations or commentary.",
                "- Do not include additional fields.",
                "- Return exactly one JSON object.",
            ]
        )
