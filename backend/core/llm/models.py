from __future__ import annotations

import os

from backend.core.path_validation import get_repo_root
from backend.core.registry import load_modules_config

# DeepSeek V4 official model IDs (api-docs.deepseek.com, 2026)
DEFAULT_SCREENING_MODEL = "deepseek-v4-pro"
DEFAULT_VERIFY_MODEL = "deepseek-v4-pro"
DEFAULT_TRANSLATE_MODEL = "deepseek-v4-flash"

_ROLE_CONFIG_KEY = {
    "screening": "screening_model",
    "verify": "verify_model",
    "translate": "translate_model",
}

_ROLE_ENV_KEY = {
    "screening": "LLM_SCREENING_MODEL",
    "verify": "LLM_VERIFY_MODEL",
    "translate": "LLM_TRANSLATE_MODEL",
}

_ROLE_DEFAULT = {
    "screening": DEFAULT_SCREENING_MODEL,
    "verify": DEFAULT_VERIFY_MODEL,
    "translate": DEFAULT_TRANSLATE_MODEL,
}


def resolve_llm_model(role: str) -> str:
    env_key = _ROLE_ENV_KEY.get(role)
    if env_key:
        override = os.environ.get(env_key, "").strip()
        if override:
            return override

    config = load_modules_config(get_repo_root()).get("llm", {})
    config_key = _ROLE_CONFIG_KEY.get(role)
    if config_key and config.get(config_key):
        return str(config[config_key])

    return _ROLE_DEFAULT.get(role, DEFAULT_VERIFY_MODEL)


STRUCTURED_JSON_ROLES = frozenset({"screening", "verify"})


def deepseek_completion_options(*, role: str, model: str) -> dict[str, str]:
    """V4 thinking mode: disabled for structured JSON and flash translation."""
    if role == "translate" or "flash" in model:
        return {"thinking": "disabled"}
    if role in STRUCTURED_JSON_ROLES:
        return {"thinking": "disabled"}
    return {"thinking": "disabled"}
