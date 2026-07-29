from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from backend.core.path_validation import get_repo_root


def default_db_path(repo_root: Path | None = None) -> Path:
    root = repo_root or get_repo_root()
    return root / "backend" / "data" / "app.db"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: Path | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                config_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS scans (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                results_dir TEXT,
                started_at TEXT,
                finished_at TEXT,
                error TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            CREATE TABLE IF NOT EXISTS findings (
                id TEXT PRIMARY KEY,
                scan_id TEXT NOT NULL,
                project TEXT NOT NULL,
                severity TEXT NOT NULL,
                confidence REAL NOT NULL,
                source TEXT NOT NULL,
                rule_id TEXT NOT NULL,
                file TEXT NOT NULL,
                line INTEGER NOT NULL,
                message TEXT NOT NULL,
                evidence TEXT NOT NULL,
                cwe TEXT NOT NULL,
                status TEXT NOT NULL,
                verified INTEGER NOT NULL,
                verify_note TEXT NOT NULL,
                remediation TEXT NOT NULL,
                FOREIGN KEY(scan_id) REFERENCES scans(id)
            );
            """
        )
        conn.commit()
