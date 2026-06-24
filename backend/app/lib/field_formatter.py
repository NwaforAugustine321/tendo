import json
import logging

logger = logging.getLogger(__name__)


def format_user_input(raw_input: str) -> str:
    """
    If the user input is a JSON array of field responses (from InputCard),
    reformat it into readable key-value text for the agent.

    Input: [{"name":"business_name","answer":"Mario store"},{"name":"location","answer":"Maryland"}]
    Output:
    business_name: Mario store
    location: Maryland
    """
    if not raw_input or not raw_input.strip().startswith("["):
        return raw_input

    try:
        responses = json.loads(raw_input)
        if not isinstance(responses, list) or not responses:
            return raw_input

        if not all(isinstance(r, dict) and "answer" in r for r in responses):
            return raw_input

        lines = []
        for resp in responses:
            name = resp.get("label") or resp.get("name", "")
            description = resp.get("description", "")
            answer = resp.get("answer", "")

            if name:
                lines.append(f"{name}: {answer}")
                if description:
                    lines.append(f"  ({description})")
            else:
                lines.append(answer)

        return "\n".join(lines).strip()

    except (json.JSONDecodeError, TypeError, KeyError):
        return raw_input
