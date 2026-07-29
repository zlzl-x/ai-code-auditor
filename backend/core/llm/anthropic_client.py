from __future__ import annotations

import json
import os
from typing import Any

from backend.core.llm.client import LLMClient, LLMResponse
from backend.core.llm.json_parse import parse_json_response as _parse_json_response


class AnthropicClient:
    def __init__(self, model: str) -> None:
        self.model = model
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for AnthropicClient")
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError("anthropic package is required") from exc
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(self, system: str, user: str, *, max_tokens: int = 1024, thinking: str | None = None, reasoning_effort: str | None = None, json_mode: bool = False) -> LLMResponse:
        message = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = ""
        for block in message.content:
            if hasattr(block, "text"):
                text += block.text
        return LLMResponse(
            text=text,
            tokens_in=message.usage.input_tokens,
            tokens_out=message.usage.output_tokens,
            model=self.model,
        )


class MockLLMClient:
    """Test client returning deterministic JSON based on prompt content."""

    def __init__(self, model: str = "mock-model") -> None:
        self.model = model

    def complete(self, system: str, user: str, *, max_tokens: int = 1024, thinking: str | None = None, reasoning_effort: str | None = None, json_mode: bool = False) -> LLMResponse:
        if "Translate this audit report section" in user or "翻译" in system:
            return LLMResponse(
                text=f"[ZH] {user.split(chr(10), 1)[-1][:200]}",
                tokens_in=150,
                tokens_out=100,
                model=self.model,
            )

        if "Analyze this file" in user:
            payload = {"findings": []}
            if "eval(" in user or "shell" in user.lower():
                payload = {
                    "findings": [
                        {
                            "rule_id": "llm.shell-exec",
                            "severity": "high",
                            "confidence": 0.85,
                            "line": 1,
                            "message": "Potential shell execution",
                            "evidence": "eval(",
                            "cwe": "CWE-78",
                            "remediation": "Avoid dynamic execution",
                        }
                    ]
                }
            return LLMResponse(
                text=json.dumps(payload),
                tokens_in=100,
                tokens_out=50,
                model=self.model,
            )

        verdict = "confirm"
        severity = "high"
        if "spawn-shell" in user or "B603" in user:
            verdict = "confirm"
        elif "false-positive-marker" in user:
            verdict = "reject"
        elif "downgrade-marker" in user:
            verdict = "downgrade"
            severity = "medium"

        payload = {
            "verdict": verdict,
            "confidence": 0.9,
            "severity": severity,
            "reasoning": f"mock verdict: {verdict}",
        }
        return LLMResponse(
            text=json.dumps(payload),
            tokens_in=200,
            tokens_out=80,
            model=self.model,
        )


def parse_json_response(text: str) -> dict[str, Any]:
    return _parse_json_response(text)


def get_llm_client(model: str, *, role: str = "default") -> LLMClient:
    from backend.core.llm.factory import get_llm_client as _get_llm_client

    return _get_llm_client(model, role=role)
