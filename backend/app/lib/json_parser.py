import json
from typing import Any
import dirtyjson
from json_repair import repair_json


def parse_json_output(raw: str, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    clean = raw.strip()
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
                return json.loads(clean[start:i + 1])
    return dirtyjson.loads(clean)
