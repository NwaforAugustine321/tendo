import json
from typing import Any
import dirtyjson
from json_repair import repair_json


def parse_json_output(raw: str, fallback: dict[str, Any] | None = None) -> dict[str, Any] | str:

    clean = raw.strip()
    if not clean:
        return fallback if fallback is not None else ""

    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    start = clean.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(clean)):
            if clean[i] == "{":
                depth += 1
            elif clean[i] == "}":
                depth -= 1
            if depth == 0:
                try:
                    return json.loads(clean[start:i + 1])
                except (json.JSONDecodeError, ValueError):
                    break

    # Try dirtyjson as a last resort, but only if it looks like JSON
    if clean.startswith("{") or clean.startswith("["):
        try:
            return dirtyjson.loads(clean)
        except Exception:
            pass

    # Not JSON — return as plain text
    return raw.strip()
