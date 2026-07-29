from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from hashlib import sha256
from typing import Any
from uuid import uuid4

import feedparser


@dataclass(frozen=True)
class KnowledgeItem:
    id: str
    title: str
    url: str
    source: str
    source_type: str
    published_at: str
    summary: str
    category: str = "blog"
    score: float = 0.0
    seen: bool = False


def _parse_published(entry: dict[str, Any]) -> str:
    published = entry.get("published") or entry.get("updated")
    if not published:
        return datetime.utcnow().isoformat() + "Z"
    try:
        return parsedate_to_datetime(published).isoformat()
    except (TypeError, ValueError, IndexError):
        return datetime.utcnow().isoformat() + "Z"


def _item_id(source_id: str, url: str) -> str:
    digest = sha256(f"{source_id}:{url}".encode("utf-8")).hexdigest()
    return digest[:32]


def fetch_rss_feed(source: dict[str, Any]) -> list[KnowledgeItem]:
    parsed = feedparser.parse(source["url"])
    items: list[KnowledgeItem] = []
    for entry in parsed.entries:
        url = str(entry.get("link", "")).strip()
        if not url:
            continue
        title = str(entry.get("title", "Untitled")).strip()
        summary = str(entry.get("summary", "")).strip()
        items.append(
            KnowledgeItem(
                id=_item_id(source["id"], url),
                title=title,
                url=url,
                source=source["id"],
                source_type="rss",
                published_at=_parse_published(entry),
                summary=summary,
                category=str(source.get("category", "blog")),
                score=float(source.get("trust_score", 0)),
            )
        )
    return items


def load_rss_sources(sources_path) -> list[dict[str, Any]]:
    import yaml
    from pathlib import Path

    data = yaml.safe_load(Path(sources_path).read_text(encoding="utf-8")) or {}
    return [source for source in data.get("sources", []) if source.get("type") == "rss"]
