from __future__ import annotations

import os

from backend.core.llm.client import LLMClient, LLMResponse

DEFAULT_BASE_URL = "https://api.deepseek.com"


class DeepSeekClient:
    def __init__(self, model: str) -> None:
        self.model = model
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required for DeepSeekClient")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for DeepSeekClient") from exc
        base_url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 1024,
        thinking: str | None = None,
        reasoning_effort: str | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        extra_body: dict[str, object] = {}
        if thinking is not None:
            extra_body["thinking"] = {"type": thinking}
        if reasoning_effort is not None:
            extra_body["reasoning_effort"] = reasoning_effort
        if json_mode:
            extra_body["response_format"] = {"type": "json_object"}

        request_kwargs: dict[str, object] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if extra_body:
            request_kwargs["extra_body"] = extra_body

        response = self._client.chat.completions.create(**request_kwargs)
        choice = response.choices[0].message.content or ""
        usage = response.usage
        return LLMResponse(
            text=choice,
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
            model=self.model,
        )
