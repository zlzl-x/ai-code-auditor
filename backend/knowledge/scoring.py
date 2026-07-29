from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from backend.knowledge.fetchers.rss import KnowledgeItem


def load_keywords_config(path: Path | None = None) -> dict[str, Any]:
    from backend.core.path_validation import get_repo_root

    config_path = path or (get_repo_root() / "backend" / "knowledge" / "keywords.yaml")
    if not config_path.is_file():
        return {}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def _title_tokens(text: str) -> set[str]:
    return {token.lower() for token in text.split() if token}


def _jaccard(a: set[str], b: set[str]) -> float:
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _keyword_hits(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lowered)


def _recency_bonus(published_at: str, days: int, bonus: float) -> float:
    try:
        published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return bonus if published >= cutoff else 0.0


def score_item(item: KnowledgeItem, config: dict[str, Any]) -> float:
    text = f"{item.title} {item.summary}"
    must_any = config.get("must_match_any", [])
    if must_any and _keyword_hits(text, must_any) == 0:
        return 0.0

    weight = float(config.get("keyword_weight", 1.5))
    boost_hits = _keyword_hits(text, config.get("boost", []))
    must_hits = _keyword_hits(text, must_any)
    base = float(item.score)
    recency = _recency_bonus(
        item.published_at,
        int(config.get("recency_days", 14)),
        float(config.get("recency_bonus", 2.0)),
    )
    seen_penalty = float(config.get("seen_penalty", 1.0)) if item.seen else 0.0
    return base + (must_hits + boost_hits) * weight + recency - seen_penalty


def dedupe_items(items: list[KnowledgeItem]) -> list[KnowledgeItem]:
    by_url: dict[str, KnowledgeItem] = {}
    for item in items:
        existing = by_url.get(item.url)
        if existing is None or item.score > existing.score:
            by_url[item.url] = item

    deduped = list(by_url.values())
    kept: list[KnowledgeItem] = []
    for item in deduped:
        tokens = _title_tokens(item.title)
        duplicate = False
        for index, other in enumerate(kept):
            if _jaccard(tokens, _title_tokens(other.title)) > 0.85:
                if item.score > other.score:
                    kept[index] = item
                duplicate = True
                break
        if not duplicate:
            kept.append(item)
    return kept


def rescore_all(items: list[KnowledgeItem], config: dict[str, Any] | None = None) -> list[KnowledgeItem]:
    cfg = config or load_keywords_config()
    scored = [
        KnowledgeItem(
            id=item.id,
            title=item.title,
            url=item.url,
            source=item.source,
            source_type=item.source_type,
            published_at=item.published_at,
            summary=item.summary,
            category=item.category,
            score=score_item(item, cfg),
            seen=item.seen,
        )
        for item in items
    ]
    return dedupe_items(scored)
