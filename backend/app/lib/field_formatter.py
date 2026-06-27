import json
import logging

logger = logging.getLogger(__name__)


def format_user_input(raw_input: str, pending_question: str | None = None) -> str:
    """
    If the user input is a JSON array of field responses (from InputCard),
    reformat it into readable key-value text for the agent.

    If the input is plain text and pending_question is set (from graph state),
    prefix it with context so the agent knows it's a response to its prior question.

    Input: [{"name":"business_name","answer":"Mario store"},{"name":"location","answer":"Maryland"}]
    Output:
    business_name: Mario store
    location: Maryland
    """
    if not raw_input:
        return raw_input

    # JSON array response from InputCard
    if raw_input.strip().startswith("["):
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

    # Plain text response — if agent previously asked a question, provide context
    if pending_question:
        return (
            f"[USER RESPONSE TO YOUR PREVIOUS QUESTION]\n"
            f"You previously asked: \"{pending_question}\"\n"
            f"The user replied: \"{raw_input}\"\n"
            f"Now proceed with the action using this answer. Do NOT ask the same question again."
        )

    return raw_input


async def classify_user_choice(
    user_text: str,
    field_choices: list[dict],
) -> str:
    """Classify free-text user input into one of the predefined field choices.
    
    Args:
        user_text: The user's raw text response.
        field_choices: List of field dicts with at least 'id' and 'label' keys.

    Returns:
        The classified label if matched, or the original user_text if not.
    """
    if not user_text or not field_choices:
        return user_text

    # Check for exact match first — skip LLM if matched
    normalized = user_text.strip().lower()
    for field in field_choices:
        if normalized == field.get("id", "").lower():
            return field.get("label", user_text)
        if normalized == field.get("label", "").lower():
            return field.get("label", user_text)

    # No exact match — use LLM classification
    from app.lib.i18n import _get_i18n
    from app.llm.client import get_client

    i18n = _get_i18n()
    prompt_template = i18n.get("slices.human_feedback_collapse")
    if not prompt_template:
        return user_text

    outcomes = ", ".join(f.get("label", f.get("id", "")) for f in field_choices)

    try:
        llm = get_client()
        messages = [
            {"role": "user", "content": prompt_template.format(
                feedback=user_text,
                outcomes=outcomes,
            )},
        ]
        response = await llm.ainvoke(messages)
        classified = response.content.strip() if response.content else ""

        # Verify the classification is one of the valid outcomes
        valid_labels = {f.get("label", "").lower(): f.get("label", "") for f in field_choices}
        if classified.lower() in valid_labels:
            return valid_labels[classified.lower()]

        # Not a valid outcome — return original
        return user_text
    except Exception as e:
        logger.debug(f"Choice classification failed: {e}")
        return user_text


