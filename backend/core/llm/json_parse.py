from __future__ import annotations

import json
import re
from typing import Any


def _strip_bom(text: str) -> str:
    return text.lstrip("\ufeff").strip()


def _extract_fence(text: str) -> str | None:
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    return None


def _extract_balanced_json(text: str) -> str | None:
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start < 0:
            continue
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
                continue
            if char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
    return None


def parse_json_response(text: str) -> dict[str, Any]:
    cleaned = _strip_bom(text)
    if not cleaned:
        raise json.JSONDecodeError("empty response", cleaned, 0)

    candidates = [cleaned]
    fenced = _extract_fence(cleaned)
    if fenced:
        candidates.insert(0, fenced)
    balanced = _extract_balanced_json(cleaned)
    if balanced:
        candidates.append(balanced)

    last_error: json.JSONDecodeError | None = None
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, list):
            return {"findings": payload}
    if last_error is not None:
        raise last_error
    raise json.JSONDecodeError("no JSON object found", cleaned, 0)
