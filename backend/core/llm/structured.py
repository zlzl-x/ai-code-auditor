from __future__ import annotations

from typing import Any

from backend.core.llm.client import LLMResponse
from backend.core.llm.json_parse import parse_json_response
from backend.core.llm.models import deepseek_completion_options
from backend.core.llm.deepseek_client import DeepSeekClient


def complete_json(
    client,
    *,
    role: str,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 2048,
) -> tuple[dict[str, Any], LLMResponse]:
    options = deepseek_completion_options(role=role, model=model)
    complete_kwargs: dict[str, Any] = {
        "max_tokens": max_tokens,
        "thinking": options.get("thinking"),
        "reasoning_effort": options.get("reasoning_effort"),
    }
    if isinstance(client, DeepSeekClient):
        complete_kwargs["json_mode"] = True

    response = client.complete(system, user, **complete_kwargs)
    return parse_json_response(response.text), response
