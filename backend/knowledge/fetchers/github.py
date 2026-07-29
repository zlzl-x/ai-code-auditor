from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.knowledge.fetchers.rss import KnowledgeItem, _item_id


def load_github_sources(sources_path) -> list[dict[str, Any]]:
    import yaml
    from pathlib import Path

    data = yaml.safe_load(Path(sources_path).read_text(encoding="utf-8")) or {}
    return [source for source in data.get("sources", []) if source.get("type") == "github"]


def fetch_github_releases(source: dict[str, Any]) -> list[KnowledgeItem]:
    repo = str(source.get("repo", "")).strip()
    if not repo or "/" not in repo:
        return []

    url = f"https://api.github.com/repos/{repo}/releases"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "ai-code-auditor"}
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:  # nosec B310 - fixed GitHub API host
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return []

    if not isinstance(payload, list):
        return []

    items: list[KnowledgeItem] = []
    for release in payload[:10]:
        tag = str(release.get("tag_name", "")).strip()
        name = str(release.get("name", tag or "Release")).strip()
        html_url = str(release.get("html_url", "")).strip()
        if not html_url:
            continue
        published = str(release.get("published_at", datetime.utcnow().isoformat() + "Z"))
        summary = str(release.get("body", "")).strip()[:500]
        title = f"{repo} {name}".strip()
        items.append(
            KnowledgeItem(
                id=_item_id(source["id"], html_url),
                title=title,
                url=html_url,
                source=source["id"],
                source_type="github",
                published_at=published,
                summary=summary,
                category=str(source.get("category", "tool")),
                score=float(source.get("trust_score", 0)),
            )
        )
    return items
