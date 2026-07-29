from backend.knowledge.fetchers.rss import KnowledgeItem
from backend.knowledge.scoring import dedupe_items, rescore_all


def test_keyword_scoring_requires_must_match() -> None:
    config = {
        "must_match_any": ["LLM", "security"],
        "boost": ["harness"],
        "keyword_weight": 2.0,
        "min_score": 6,
    }
    relevant = KnowledgeItem(
        id="1",
        title="LLM agent security",
        url="https://example.com/a",
        source="src",
        source_type="rss",
        published_at="2026-07-01T00:00:00+00:00",
        summary="prompt injection harness",
        score=1.0,
    )
    irrelevant = KnowledgeItem(
        id="2",
        title="Cooking recipes",
        url="https://example.com/b",
        source="src",
        source_type="rss",
        published_at="2026-07-01T00:00:00+00:00",
        summary="pasta",
        score=1.0,
    )
    scored = rescore_all([relevant, irrelevant], config)
    scores = {item.url: item.score for item in scored}
    assert scores["https://example.com/a"] > 0
    assert scores.get("https://example.com/b", 0) == 0


def test_dedupe_by_url() -> None:
    items = [
        KnowledgeItem(
            id="1",
            title="A",
            url="https://example.com/x",
            source="s",
            source_type="rss",
            published_at="2026-01-01",
            summary="",
            score=1.0,
        ),
        KnowledgeItem(
            id="2",
            title="A duplicate",
            url="https://example.com/x",
            source="s",
            source_type="rss",
            published_at="2026-01-01",
            summary="",
            score=5.0,
        ),
    ]
    deduped = dedupe_items(items)
    assert len(deduped) == 1
    assert deduped[0].score == 5.0
