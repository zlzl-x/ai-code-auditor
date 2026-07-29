from backend.knowledge.backlog import build_backlog, write_backlog
from backend.knowledge.fetchers.rss import KnowledgeItem
from backend.knowledge.storage import KnowledgeStorage


def test_build_backlog_filters_keywords(tmp_path) -> None:
    db_path = tmp_path / "feed.db"
    storage = KnowledgeStorage(db_path)
    items = [
        KnowledgeItem(
            id="1",
            title="semgrep release notes",
            url="https://example.com/1",
            source="semgrep-blog",
            source_type="rss",
            published_at="2024-01-01T00:00:00Z",
            summary="new semgrep rules",
            score=8.5,
        ),
        KnowledgeItem(
            id="2",
            title="unrelated post",
            url="https://example.com/2",
            source="other",
            source_type="rss",
            published_at="2024-01-02T00:00:00Z",
            summary="cooking tips",
            score=9.0,
        ),
    ]
    storage.upsert_items(items)
    backlog = build_backlog(storage, limit=10)
    assert len(backlog) == 1
    assert backlog[0]["id"] == "1"
    assert backlog[0]["suggested_action"] == "update_rule_pack_or_detector"


def test_write_backlog_persists_file(tmp_path) -> None:
    db_path = tmp_path / "feed.db"
    storage = KnowledgeStorage(db_path)
    storage.upsert_items(
        [
            KnowledgeItem(
                id="1",
                title="gitleaks release",
                url="https://example.com/1",
                source="gitleaks",
                source_type="github",
                published_at="2024-01-01T00:00:00Z",
                summary="new gitleaks patterns",
                score=8.0,
            )
        ]
    )
    backlog = write_backlog(storage, limit=5, repo_root=tmp_path)
    assert len(backlog) == 1
    assert (tmp_path / "knowledge" / "auto_backlog.json").is_file()
