import json
from unittest.mock import patch

from backend.core.llm.client import LLMResponse
from backend.knowledge.curate import curate_top_items
from backend.knowledge.fetchers.rss import KnowledgeItem
from backend.knowledge.storage import KnowledgeStorage


def test_curate_top_items_updates_summary(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AUTO_LLM_CURATE", "true")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    storage = KnowledgeStorage(tmp_path / "feed.db")
    storage.upsert_items(
        [
            KnowledgeItem(
                id="item-1",
                title="Harness update",
                url="https://example.com/harness",
                source="harness",
                source_type="github",
                published_at="2024-01-01T00:00:00Z",
                summary="",
                score=9.0,
            )
        ]
    )

    class FakeClient:
        def __init__(self, model: str) -> None:
            self.model = model

        def complete(self, system: str, user: str) -> LLMResponse:
            return LLMResponse(
                text=json.dumps(
                    {"one_line_summary": "New harness release", "category": "methodology"}
                ),
                tokens_in=10,
                tokens_out=5,
                model="deepseek-chat",
            )

    with patch("backend.core.llm.deepseek_client.DeepSeekClient", FakeClient):
        updated = curate_top_items(storage, limit=1, repo_root=tmp_path)

    assert updated == 1
    rows = storage.list_items(limit=1)
    assert rows[0]["summary"] == "New harness release"
    assert rows[0]["category"] == "methodology"


def test_curate_skips_without_api_key(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AUTO_LLM_CURATE", "true")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    storage = KnowledgeStorage(tmp_path / "feed.db")
    assert curate_top_items(storage, repo_root=tmp_path) == 0
