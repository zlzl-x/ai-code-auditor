from unittest.mock import patch

from backend.knowledge.fetchers.rss import fetch_rss_feed


def test_fetch_rss_feed_normalizes_entries() -> None:
    source = {
        "id": "demo-feed",
        "type": "rss",
        "url": "https://example.com/feed",
        "category": "blog",
        "trust_score": 8,
    }
    fake_feed = type(
        "Feed",
        (),
        {
            "entries": [
                {
                    "title": "Security update",
                    "link": "https://example.com/post-1",
                    "summary": "summary",
                    "published": "Mon, 01 Jan 2024 00:00:00 GMT",
                }
            ]
        },
    )()
    with patch("backend.knowledge.fetchers.rss.feedparser.parse", return_value=fake_feed):
        items = fetch_rss_feed(source)
    assert len(items) == 1
    assert items[0].title == "Security update"
    assert items[0].source == "demo-feed"
