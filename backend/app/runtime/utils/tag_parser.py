from __future__ import annotations

import json
import re


def extract_tag(
    text: str,
    tag: str,
) -> str:
    """


    Extraction therefore:
    - finds all complete occurrences,
    - prefers the last non-empty occurrence,
    - falls back to the last incomplete occurrence,
    - never consumes another tag,
    - returns only the tag value.
    """

    if not text or not tag:
        return ""

    escaped_tag = re.escape(tag)

    closed_matches = re.findall(
        rf"<{escaped_tag}>\s*(.*?)\s*</{escaped_tag}>",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if closed_matches:
        for value in reversed(closed_matches):
            value = value.strip()

            if not value:
                continue

            # Remove accidental surrounding quotes.
            if (
                len(value) >= 2
                and value[0] == '"'
                and value[-1] == '"'
            ):
                value = value[1:-1].strip()

            return value

    fallback_matches = re.findall(
        rf"<{escaped_tag}>\s*([^<]*)",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if fallback_matches:
        for value in reversed(fallback_matches):
            value = value.strip()

            if not value:
                continue

            if (
                len(value) >= 2
                and value[0] == '"'
                and value[-1] == '"'
            ):
                value = value[1:-1].strip()

            return value

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
        return json.loads(raw)
    except (
        json.JSONDecodeError,
        TypeError,
    ):
        pass

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
