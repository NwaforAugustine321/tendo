"""Text utility functions for agent output processing."""

import json
import re


def strip_internal_reasoning(text: str) -> str:
    """Remove internal agent reasoning XML tags from text shown to users."""
    if not text:
        return text

    # Extract <Final_Answer> content
    fa_match = re.search(r"<Final_Answer>(.*?)(?:</Final_Answer>|$)", text, re.DOTALL)
    if fa_match:
        answer = fa_match.group(1).strip()
        if answer.startswith("{"):
            try:
                data = json.loads(answer)
                return data.get("response", answer)
            except (json.JSONDecodeError, ValueError):
                pass
        return answer

    # Strip all XML reasoning tags — return remaining content
    stripped = re.sub(r"<Thought>.*?</Thought>", "", text, flags=re.DOTALL)
    stripped = re.sub(r"<Action>.*?</Action>", "", stripped, flags=re.DOTALL)
    stripped = re.sub(r"<Action_Input>.*?</Action_Input>", "", stripped, flags=re.DOTALL)
    stripped = re.sub(r"<Observation>.*?</Observation>", "", stripped, flags=re.DOTALL)
    stripped = stripped.strip()
    if stripped:
        return stripped

    # If everything was inside tags, use thought content as fallback
    thought_match = re.search(r"<Thought>(.*?)</Thought>", text, re.DOTALL)
    if thought_match:
        return thought_match.group(1).strip()

    return text
