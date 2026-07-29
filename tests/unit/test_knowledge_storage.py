from backend.knowledge.fetchers.rss import KnowledgeItem
from backend.knowledge.storage import KnowledgeStorage


def test_knowledge_storage_upsert_and_list(tmp_path) -> None:
    storage = KnowledgeStorage(tmp_path / "feed.db")
    items = [
        KnowledgeItem(
            id="item-1",
            title="Post A",
            url="https://example.com/a",
            source="demo",
            source_type="rss",
            published_at="2024-01-01T00:00:00Z",
            summary="A",
            category="blog",
            score=8.0,
        )
    ]
    storage.upsert_items(items)
    listed = storage.list_items(limit=10)
    assert len(listed) == 1
    assert listed[0]["title"] == "Post A"
