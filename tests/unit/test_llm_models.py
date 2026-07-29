from backend.core.llm.models import (
    DEFAULT_SCREENING_MODEL,
    DEFAULT_TRANSLATE_MODEL,
    DEFAULT_VERIFY_MODEL,
    deepseek_completion_options,
    resolve_llm_model,
)


def test_default_models() -> None:
    assert DEFAULT_VERIFY_MODEL == "deepseek-v4-pro"
    assert DEFAULT_SCREENING_MODEL == "deepseek-v4-pro"
    assert DEFAULT_TRANSLATE_MODEL == "deepseek-v4-flash"


def test_deepseek_completion_options_pro_vs_flash() -> None:
    pro_opts = deepseek_completion_options(role="verify", model="deepseek-v4-pro")
    assert pro_opts == {"thinking": "disabled"}

    flash_opts = deepseek_completion_options(role="translate", model="deepseek-v4-flash")
    assert flash_opts == {"thinking": "disabled"}


def test_resolve_llm_model_from_env(monkeypatch) -> None:
    monkeypatch.setenv("LLM_TRANSLATE_MODEL", "custom-flash")
    assert resolve_llm_model("translate") == "custom-flash"
