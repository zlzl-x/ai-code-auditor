from __future__ import annotations

import os

from backend.core.llm.client import LLMClient
from backend.core.path_validation import get_repo_root
from backend.core.registry import load_modules_config


def resolve_llm_provider(role: str = "default") -> str:
    env_by_role = {
        "screening": "LLM_SCREENING_CLIENT",
        "verify": "LLM_VERIFY_CLIENT",
        "translate": "LLM_TRANSLATE_CLIENT",
    }
    if role in env_by_role:
        override = os.environ.get(env_by_role[role], "").strip().lower()
        if override:
            return override

    global_client = os.environ.get("LLM_CLIENT", "").strip().lower()
    if global_client:
        return global_client

    config = load_modules_config(get_repo_root()).get("llm", {})
    if role in ("screening", "verify", "translate"):
        role_provider = config.get(f"{role}_provider")
        if role_provider:
            return str(role_provider).lower()
    return str(config.get("provider", "deepseek")).lower()


def is_provider_configured(provider: str) -> bool:
    if provider == "deepseek":
        return bool(os.environ.get("DEEPSEEK_API_KEY"))
    if provider == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    if provider == "mock":
        return True
    return False


def get_llm_client(model: str, *, role: str = "default") -> LLMClient:
    provider = resolve_llm_provider(role)
    if provider == "mock":
        from backend.core.llm.anthropic_client import MockLLMClient

        return MockLLMClient(model=model)
    if provider == "deepseek":
        from backend.core.llm.deepseek_client import DeepSeekClient

        return DeepSeekClient(model=model)
    from backend.core.llm.anthropic_client import AnthropicClient

    return AnthropicClient(model=model)
