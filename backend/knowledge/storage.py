from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.knowledge.fetchers.rss import KnowledgeItem


class KnowledgeStorage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    category TEXT NOT NULL,
                    score REAL NOT NULL DEFAULT 0,
                    seen INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.commit()

    def upsert_items(self, items: list[KnowledgeItem]) -> int:
        inserted = 0
        with self._connect() as conn:
            for item in items:
                cursor = conn.execute(
                    """
                    INSERT INTO items (
                        id, title, url, source, source_type,
                        published_at, summary, category, score, seen
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        title=excluded.title,
                        summary=excluded.summary,
                        published_at=excluded.published_at,
                        score=excluded.score
                    """,
                    (
                        item.id,
                        item.title,
                        item.url,
                        item.source,
                        item.source_type,
                        item.published_at,
                        item.summary,
                        item.category,
                        item.score,
                        int(item.seen),
                    ),
                )
                if cursor.rowcount:
                    inserted += 1
            conn.commit()
        return inserted

    def list_items(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM items
                ORDER BY published_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_top(self, limit: int = 20, min_score: float = 0.0) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM items
                WHERE score >= ?
                ORDER BY score DESC, published_at DESC
                LIMIT ?
                """,
                (min_score, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def update_scores(self, items: list[dict]) -> int:
        updated = 0
        with self._connect() as conn:
            for item in items:
                conn.execute(
                    "UPDATE items SET score = ? WHERE id = ?",
                    (item["score"], item["id"]),
                )
                updated += 1
            conn.commit()
        return updated

    def fetch_all_items(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM items").fetchall()
        return [dict(row) for row in rows]

    def mark_seen(self, item_id: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE items SET seen = 1 WHERE id = ?", (item_id,))
            conn.commit()

    def ignore_source(self, source_id: str) -> None:
        from backend.core.path_validation import get_repo_root

        path = get_repo_root() / "backend" / "knowledge" / "ignored_sources.yaml"
        import yaml

        data = {"ignored": []}
        if path.is_file():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {"ignored": []}
        ignored = set(data.get("ignored", []))
        ignored.add(source_id)
        data["ignored"] = sorted(ignored)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        with self._connect() as conn:
            conn.execute("DELETE FROM items WHERE source = ?", (source_id,))
            conn.commit()

    def update_summary(self, item_id: str, summary: str, category: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE items SET summary = ?, category = ? WHERE id = ?",
                (summary, category, item_id),
            )
            conn.commit()

    def list_backlog(self, limit: int = 20, min_score: float = 0.0) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM items
                WHERE seen = 0 AND score >= ?
                ORDER BY score DESC, published_at DESC
                LIMIT ?
                """,
                (min_score, limit),
            ).fetchall()
        return [dict(row) for row in rows]
