import json
from unittest.mock import patch

from backend.knowledge.fetchers.github import fetch_github_releases


def test_fetch_github_releases_maps_items() -> None:
    source = {
        "id": "semgrep-releases",
        "type": "github",
        "repo": "semgrep/semgrep",
        "category": "tool",
        "trust_score": 8,
    }
    payload = [
        {
            "tag_name": "v1.0.0",
            "name": "v1.0.0",
            "html_url": "https://github.com/semgrep/semgrep/releases/tag/v1.0.0",
            "published_at": "2024-01-01T00:00:00Z",
            "body": "Security fixes",
        }
    ]

    class FakeResponse:
        def read(self):
            return json.dumps(payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    with patch("backend.knowledge.fetchers.github.urlopen", return_value=FakeResponse()):
        items = fetch_github_releases(source)

    assert len(items) == 1
    assert items[0].source == "semgrep-releases"
    assert items[0].source_type == "github"
    assert "semgrep/semgrep" in items[0].title
