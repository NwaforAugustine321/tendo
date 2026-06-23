"""Format structured field responses from the frontend for the agent."""

import json
import logging

logger = logging.getLogger(__name__)


def format_user_input(raw_input: str) -> str:
    """
    If the user input is a JSON array of field responses (from InputCard),
    reformat it into a readable string for the agent.

    Input format (from frontend):
    [{"name": "business_name", "label": "Business Name", "description": "hint", "answer": "Flivana"}]

    Output format (for agent):
    Label: Business Name
    Description: hint
    User answer: Flivana
    """
    if not raw_input or not raw_input.strip().startswith("["):
        return raw_input

    try:
        responses = json.loads(raw_input)
        if not isinstance(responses, list) or not responses:
            return raw_input

        # Verify it's structured field data
        if not all(isinstance(r, dict) and "answer" in r for r in responses):
            return raw_input

        lines = []
        for resp in responses:
            label = resp.get("label")
            description = resp.get("description", "")
            answer = resp.get("answer", "")

            if label:
                # Option/choice response — include context
                lines.append(f"Label: {label}")
                if description:
                    lines.append(f"Description: {description}")
                lines.append(f"User answer: {answer}")
                lines.append("")
            else:
                # Plain text response — just the answer
                lines.append(answer)

        return "\n".join(lines).strip()

    except (json.JSONDecodeError, TypeError, KeyError):
        return raw_input
