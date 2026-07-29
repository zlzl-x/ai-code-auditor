from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from backend.core.context import Finding, FindingStatus
from backend.core.path_validation import get_repo_root
from backend.models.database import default_db_path, get_connection, init_db


class AppRepository:
    def __init__(self, db_path: Path | None = None, repo_root: Path | None = None) -> None:
        self.db_path = db_path or default_db_path()
        self.repo_root = repo_root or get_repo_root()
        init_db(self.db_path)

    def sync_projects_from_disk(self) -> list[dict[str, Any]]:
        projects_dir = self.repo_root / "projects"
        synced: list[dict[str, Any]] = []
        if not projects_dir.is_dir():
            return synced
        for config_path in projects_dir.glob("*/config.yaml"):
            project_id = config_path.parent.name
            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            created_at = datetime.now(timezone.utc).isoformat()
            with get_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO projects (id, name, path, config_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        path=excluded.path,
                        config_json=excluded.config_json
                    """,
                    (
                        project_id,
                        data.get("name", project_id),
                        data.get("path", ""),
                        json.dumps(data, ensure_ascii=False),
                        created_at,
                    ),
                )
                conn.commit()
            synced.append(self.get_project(project_id))
        return synced

    def list_projects(self) -> list[dict[str, Any]]:
        self.sync_projects_from_disk()
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        return [self._project_row(row) for row in rows]

    def get_project(self, project_id: str) -> dict[str, Any]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            self.sync_projects_from_disk()
            with get_connection(self.db_path) as conn:
                row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            raise KeyError(project_id)
        return self._project_row(row)

    def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        project_id = payload["id"]
        config = {
            "name": payload["name"],
            "path": payload["path"],
            "languages": payload.get("languages", []),
            "scan_mode": payload.get("scan_mode", "quick"),
            "exclude": payload.get("exclude", []),
            "focus_areas": payload.get("focus_areas", []),
        }
        project_dir = self.repo_root / "projects" / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        config_path = project_dir / "config.yaml"
        config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
        created_at = datetime.now(timezone.utc).isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO projects (id, name, path, config_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    path=excluded.path,
                    config_json=excluded.config_json
                """,
                (
                    project_id,
                    config["name"],
                    config["path"],
                    json.dumps(config, ensure_ascii=False),
                    created_at,
                ),
            )
            conn.commit()
        return self.get_project(project_id)

    def create_scan(self, scan_id: str, project_id: str, mode: str) -> dict[str, Any]:
        started_at = datetime.now(timezone.utc).isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO scans (id, project_id, mode, status, started_at)
                VALUES (?, ?, ?, 'pending', ?)
                """,
                (scan_id, project_id, mode, started_at),
            )
            conn.commit()
        return self.get_scan(scan_id)

    def update_scan(
        self,
        scan_id: str,
        *,
        status: str | None = None,
        results_dir: str | None = None,
        finished_at: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        fields: list[str] = []
        values: list[Any] = []
        if status is not None:
            fields.append("status = ?")
            values.append(status)
        if results_dir is not None:
            fields.append("results_dir = ?")
            values.append(results_dir)
        if finished_at is not None:
            fields.append("finished_at = ?")
            values.append(finished_at)
        if error is not None:
            fields.append("error = ?")
            values.append(error)
        if not fields:
            return self.get_scan(scan_id)
        values.append(scan_id)
        with get_connection(self.db_path) as conn:
            conn.execute(f"UPDATE scans SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()
        return self.get_scan(scan_id)

    def get_scan(self, scan_id: str) -> dict[str, Any]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
        if row is None:
            raise KeyError(scan_id)
        scan = dict(row)
        scan["finding_count"] = self.count_findings(scan_id)
        return scan

    def list_scans(self, project_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        query = "SELECT * FROM scans"
        params: list[Any] = []
        if project_id:
            query += " WHERE project_id = ?"
            params.append(project_id)
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        with get_connection(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [self.get_scan(row["id"]) for row in rows]

    def import_findings(self, scan_id: str, findings: list[Finding]) -> int:
        with get_connection(self.db_path) as conn:
            for finding in findings:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO findings (
                        id, scan_id, project, severity, confidence, source, rule_id,
                        file, line, message, evidence, cwe, status, verified,
                        verify_note, remediation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        finding.id,
                        scan_id,
                        finding.project,
                        finding.severity.value,
                        finding.confidence,
                        finding.source,
                        finding.rule_id,
                        finding.file,
                        finding.line,
                        finding.message,
                        finding.evidence,
                        finding.cwe,
                        finding.status.value,
                        int(finding.verified),
                        finding.verify_note,
                        finding.remediation,
                    ),
                )
            conn.commit()
        return len(findings)

    def list_findings(
        self,
        *,
        scan_id: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM findings WHERE 1=1"
        params: list[Any] = []
        if scan_id:
            query += " AND scan_id = ?"
            params.append(scan_id)
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY CASE severity WHEN 'critical' THEN 5 WHEN 'high' THEN 4 WHEN 'medium' THEN 3 WHEN 'low' THEN 2 ELSE 1 END DESC LIMIT ?"
        params.append(limit)
        with get_connection(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._finding_row(row) for row in rows]

    def update_finding_status(self, finding_id: str, status: str) -> dict[str, Any]:
        if status not in {item.value for item in FindingStatus}:
            raise ValueError(f"Invalid status: {status}")
        with get_connection(self.db_path) as conn:
            conn.execute("UPDATE findings SET status = ? WHERE id = ?", (status, finding_id))
            row = conn.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
            conn.commit()
        if row is None:
            raise KeyError(finding_id)
        return self._finding_row(row)

    def get_finding(self, finding_id: str) -> dict[str, Any]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
        if row is None:
            raise KeyError(finding_id)
        return self._finding_row(row)

    def count_findings(self, scan_id: str | None = None) -> int:
        with get_connection(self.db_path) as conn:
            if scan_id:
                row = conn.execute(
                    "SELECT COUNT(*) AS c FROM findings WHERE scan_id = ?", (scan_id,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) AS c FROM findings").fetchone()
        return int(row["c"]) if row else 0

    def severity_counts(self) -> dict[str, int]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT severity, COUNT(*) AS c FROM findings GROUP BY severity"
            ).fetchall()
        return {row["severity"]: row["c"] for row in rows}

    def scans_today(self) -> int:
        today = datetime.now(timezone.utc).date().isoformat()
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM scans WHERE started_at LIKE ?",
                (f"{today}%",),
            ).fetchone()
        return int(row["c"]) if row else 0

    @staticmethod
    def _project_row(row: Any) -> dict[str, Any]:
        config = json.loads(row["config_json"])
        return {
            "id": row["id"],
            "name": row["name"],
            "path": row["path"],
            "languages": config.get("languages", []),
            "scan_mode": config.get("scan_mode", "quick"),
            "created_at": row["created_at"],
        }

    @staticmethod
    def _finding_row(row: Any) -> dict[str, Any]:
        return {
            "id": row["id"],
            "scan_id": row["scan_id"],
            "project": row["project"],
            "severity": row["severity"],
            "confidence": row["confidence"],
            "source": row["source"],
            "rule_id": row["rule_id"],
            "file": row["file"],
            "line": row["line"],
            "message": row["message"],
            "evidence": row["evidence"],
            "cwe": row["cwe"],
            "status": row["status"],
            "verified": bool(row["verified"]),
            "verify_note": row["verify_note"],
            "remediation": row["remediation"],
        }
