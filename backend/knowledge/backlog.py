from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.core.path_validation import get_repo_root
from backend.knowledge.scoring import load_keywords_config
from backend.knowledge.storage import KnowledgeStorage


BACKLOG_KEYWORDS = ("harness", "semgrep", "gitleaks", "release", "agent", "mcp")


def default_backlog_path(repo_root: Path | None = None) -> Path:
    root = repo_root or get_repo_root()
    return root / "knowledge" / "auto_backlog.json"


def _suggested_action(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    if "semgrep" in text or "gitleaks" in text:
        return "update_rule_pack_or_detector"
    if "release" in text:
        return "review_release_notes"
    if "harness" in text:
        return "evaluate_harness_pattern"
    return "review_feed_item"


def _priority(score: float) -> str:
    if score >= 9:
        return "high"
    if score >= 7:
        return "medium"
    return "low"


def build_backlog(
    storage: KnowledgeStorage,
    *,
    limit: int = 20,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    config = load_keywords_config()
    min_score = float(config.get("min_score", 6))
    rows = storage.list_backlog(limit=limit * 3, min_score=min_score)
    backlog: list[dict[str, Any]] = []
    for row in rows:
        haystack = f"{row['title']} {row['summary']}".lower()
        if not any(keyword in haystack for keyword in BACKLOG_KEYWORDS):
            continue
        backlog.append(
            {
                "id": row["id"],
                "title": row["title"],
                "suggested_action": _suggested_action(row["title"], row["summary"]),
                "priority": _priority(float(row.get("score", 0))),
                "score": float(row.get("score", 0)),
            }
        )
        if len(backlog) >= limit:
            break
    return backlog


def write_backlog(
    storage: KnowledgeStorage,
    *,
    limit: int = 20,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    root = repo_root or get_repo_root()
    backlog = build_backlog(storage, limit=limit, repo_root=root)
    path = default_backlog_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(backlog, indent=2, ensure_ascii=False), encoding="utf-8")
    return backlog


def read_backlog(repo_root: Path | None = None, *, limit: int = 20) -> list[dict[str, Any]]:
    path = default_backlog_path(repo_root)
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return data[:limit]
