from __future__ import annotations

import argparse
from pathlib import Path

from backend.core.path_validation import get_repo_root
from backend.knowledge.backlog import read_backlog, write_backlog
from backend.knowledge.curate import curate_top_items
from backend.knowledge.fetchers.github import fetch_github_releases, load_github_sources
from backend.knowledge.fetchers.rss import KnowledgeItem, fetch_rss_feed, load_rss_sources
from backend.knowledge.scoring import load_keywords_config, rescore_all
from backend.knowledge.storage import KnowledgeStorage


def default_db_path(repo_root: Path | None = None) -> Path:
    root = repo_root or get_repo_root()
    return root / "backend" / "knowledge" / "cache" / "feed.db"


def default_sources_path(repo_root: Path | None = None) -> Path:
    root = repo_root or get_repo_root()
    return root / "backend" / "knowledge" / "sources.yaml"


def _dict_to_item(row: dict) -> KnowledgeItem:
    return KnowledgeItem(
        id=row["id"],
        title=row["title"],
        url=row["url"],
        source=row["source"],
        source_type=row["source_type"],
        published_at=row["published_at"],
        summary=row["summary"],
        category=row.get("category", "blog"),
        score=float(row.get("score", 0)),
        seen=bool(row.get("seen", 0)),
    )


def refresh_feeds(repo_root: Path | None = None) -> int:
    root = repo_root or get_repo_root()
    storage = KnowledgeStorage(default_db_path(root))
    sources_path = default_sources_path(root)
    config = load_keywords_config()
    total = 0
    for source in load_rss_sources(sources_path):
        items = fetch_rss_feed(source)
        rescored = rescore_all(items, config)
        total += storage.upsert_items(rescored)
    for source in load_github_sources(sources_path):
        items = fetch_github_releases(source)
        rescored = rescore_all(items, config)
        total += storage.upsert_items(rescored)
    _rescore_existing(storage)
    write_backlog(storage, repo_root=root)
    curate_top_items(storage, repo_root=root)
    return total


def _rescore_existing(storage: KnowledgeStorage) -> None:
    config = load_keywords_config()
    rows = storage.fetch_all_items()
    items = [_dict_to_item(row) for row in rows]
    rescored = rescore_all(items, config)
    storage.update_scores([{"id": item.id, "score": item.score} for item in rescored])


def list_feeds(limit: int = 20, repo_root: Path | None = None) -> list[dict]:
    storage = KnowledgeStorage(default_db_path(repo_root))
    return storage.list_items(limit=limit)


def top_feeds(limit: int = 20, min_score: float | None = None, repo_root: Path | None = None) -> list[dict]:
    storage = KnowledgeStorage(default_db_path(repo_root))
    config = load_keywords_config()
    threshold = float(min_score if min_score is not None else config.get("min_score", 6))
    return storage.list_top(limit=limit, min_score=threshold)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Knowledge feed CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    refresh_parser = subparsers.add_parser("refresh", help="Fetch RSS sources")
    refresh_parser.set_defaults(func=lambda _args: print(f"Upserted {refresh_feeds()} items"))

    list_parser = subparsers.add_parser("list", help="List cached feed items")
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.set_defaults(
        func=lambda args: [
            print(f"- {item['title']} ({item['source']})")
            for item in list_feeds(limit=args.limit)
        ]
    )

    top_parser = subparsers.add_parser("top", help="List top-scored feed items")
    top_parser.add_argument("--limit", type=int, default=20)
    top_parser.add_argument("--min-score", type=float, default=None)
    top_parser.set_defaults(
        func=lambda args: [
            print(f"- [{item['score']:.1f}] {item['title']} ({item['source']})")
            for item in top_feeds(limit=args.limit, min_score=args.min_score)
        ]
    )

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
