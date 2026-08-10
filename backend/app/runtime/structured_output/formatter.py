from __future__ import annotations

import json


class OutputFormatter:

    def build_prompt(
        self,
        output_type: type,
    ) -> str:

        schema = json.dumps(
            output_type.model_json_schema(),
            indent=2,
        )

        return f"""
                    Return ONLY valid JSON.

                    The JSON MUST conform to this schema.

                    {schema}

                    Rules:
                    - Do not include markdown.
                    - Do not include explanations.
                    - Do not include additional text.
                    - Return exactly one JSON object.
                """
