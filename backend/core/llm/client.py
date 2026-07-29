from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMResponse:
    text: str
    tokens_in: int
    tokens_out: int
    model: str


class LLMClient(Protocol):
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
        ...
