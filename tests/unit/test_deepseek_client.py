import os
from unittest.mock import MagicMock, patch

import pytest

from backend.core.llm.factory import get_llm_client, is_provider_configured, resolve_llm_provider


def test_resolve_llm_provider_defaults_to_deepseek(repo_root, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_CLIENT", raising=False)
    monkeypatch.delenv("LLM_SCREENING_CLIENT", raising=False)
    assert resolve_llm_provider("screening") == "deepseek"


def test_resolve_llm_provider_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_VERIFY_CLIENT", "anthropic")
    assert resolve_llm_provider("verify") == "anthropic"


def test_is_provider_configured_deepseek(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    assert is_provider_configured("deepseek") is True


def test_get_llm_client_deepseek(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.delenv("LLM_CLIENT", raising=False)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"verdict":"confirm"}'))]
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
    with patch("openai.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        client = get_llm_client("deepseek-v4-pro", role="verify")
        result = client.complete("system", "user")
    assert "confirm" in result.text
    assert result.tokens_in == 10


def test_deepseek_client_json_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.delenv("LLM_CLIENT", raising=False)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"verdict":"confirm"}'))]
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
    with patch("openai.OpenAI") as mock_openai:
        client = get_llm_client("deepseek-v4-pro", role="verify")
        client.complete("system", "user", json_mode=True)
        call_kwargs = mock_openai.return_value.chat.completions.create.call_args.kwargs
    assert call_kwargs["extra_body"]["response_format"] == {"type": "json_object"}
