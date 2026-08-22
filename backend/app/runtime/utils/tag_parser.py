from __future__ import annotations

import json
import re


def extract_tag(
    text: str,
    tag: str,
) -> str:
    """
    Extract the content of a tag.

    Supports:
    - properly closed tags
    - incomplete tags where the closing tag is missing
    """

    escaped_tag = re.escape(
        tag,
    )

    # Normal closed tag.
    match = re.search(
        rf"<{escaped_tag}>\s*(.*?)\s*</{escaped_tag}>",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    # Fallback for incomplete generation.
    match = re.search(
        rf"<{escaped_tag}>\s*(.*)",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    return ""


def extract_json(
    text: str,
) -> object | None:
    """
    Extract and parse a JSON value from text.

    Handles accidental markdown fences and
    partially surrounded JSON.
    """

    raw = text.strip()

    if not raw:
        return None

    # Remove markdown fences.
    raw = re.sub(
        r"```(?:json)?",
        "",
        raw,
        flags=re.IGNORECASE,
    )

    raw = raw.replace(
        "```",
        "",
    ).strip()

    try:
        return json.loads(
            raw,
        )
    except (
        json.JSONDecodeError,
        TypeError,
    ):
        pass

    # Try to find a JSON object.
    object_match = re.search(
        r"\{.*\}",
        raw,
        re.DOTALL,
    )

    if object_match:
        try:
            return json.loads(
                object_match.group(0),
            )
        except json.JSONDecodeError:
            pass

    # Try to find a JSON array.
    array_match = re.search(
        r"\[.*\]",
        raw,
        re.DOTALL,
    )

    if array_match:
        try:
            return json.loads(
                array_match.group(0),
            )
        except json.JSONDecodeError:
            pass

    return None


def extract_json_list(
    text: str,
    tag: str | None = None,
    *,
    max_items: int = 3,
) -> list[str]:
    """
    Extract a JSON list from text.

    If ``tag`` is provided, only the content inside
    that tag is parsed.
    """

    raw = (
        extract_tag(
            text,
            tag,
        )
        if tag
        else text
    )

    if not raw:
        return []

    parsed = extract_json(
        raw,
    )

    if isinstance(
        parsed,
        list,
    ):
        return [
            str(item).strip()
            for item in parsed[:max_items]
            if str(item).strip()
        ]

    # Fallback for partially generated JSON arrays.
    values = re.findall(
        r'"((?:\\.|[^"\\])*)"',
        raw,
    )

    result: list[str] = []

    for value in values:
        try:
            value = json.loads(
                f'"{value}"',
            )
        except json.JSONDecodeError:
            continue

        value = value.strip()

        if not value:
            continue

        result.append(
            value,
        )

        if len(result) >= max_items:
            break

    return result


def parse_tagged_response(
    text: str,
    *,
    content_tags: list[str] | None = None,
    list_tags: list[str] | None = None,
    max_items: int = 3,
) -> tuple[dict[str, str], dict[str, list[str]]]:
    """
    Generic parser for tagged LLM responses.

    Returns:

        (
            {
                "tag": "content"
            },
            {
                "tag": ["item"]
            }
        )
    """

    contents = {
        tag: extract_tag(
            text,
            tag,
        )
        for tag in (
            content_tags or []
        )
    }

    lists = {
        tag: extract_json_list(
            text,
            tag,
            max_items=max_items,
        )
        for tag in (
            list_tags or []
        )
    }

    return contents, lists
