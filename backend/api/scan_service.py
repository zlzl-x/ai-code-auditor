from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.core.context import Finding
from backend.core.events import EventEmitter, ScanEvent
from backend.core.path_validation import get_repo_root
from backend.core.pipeline import run_scan
from backend.models.repository import AppRepository

_emitters: dict[str, EventEmitter] = {}
_event_log: dict[str, list[dict]] = {}


def get_emitter(scan_id: str) -> EventEmitter | None:
    return _emitters.get(scan_id)


def get_event_log(scan_id: str) -> list[dict]:
    return list(_event_log.get(scan_id, []))


def _record_event(scan_id: str, event: ScanEvent) -> None:
    payload = {
        "stage": event.stage,
        "message": event.message,
        "timestamp": event.timestamp,
        "progress": event.progress,
    }
    _event_log.setdefault(scan_id, []).append(payload)


def execute_scan(scan_id: str, project_id: str, mode: str, repo: AppRepository) -> None:
    repo_root = get_repo_root()
    emitter = EventEmitter()
    _emitters[scan_id] = emitter
    emitter.on(lambda event: _record_event(scan_id, event))

    repo.update_scan(scan_id, status="running")
    try:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
        results_dir = repo_root / "results" / project_id / timestamp
        result = run_scan(
            project_id,
            mode=mode,
            scan_id=scan_id,
            emitter=emitter,
            results_dir=results_dir,
            repo_root=repo_root,
        )
        findings = _load_findings(result.results_dir)
        repo.import_findings(scan_id, findings)
        repo.update_scan(
            scan_id,
            status="completed",
            results_dir=str(result.results_dir),
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as exc:  # noqa: BLE001
        repo.update_scan(
            scan_id,
            status="failed",
            finished_at=datetime.now(timezone.utc).isoformat(),
            error=str(exc),
        )
        emitter.emit(ScanEvent.create("error", str(exc), 1.0))
    finally:
        _emitters.pop(scan_id, None)


def create_scan_job(project_id: str, mode: str, repo: AppRepository) -> dict:
    scan_id = str(uuid4())
    return repo.create_scan(scan_id, project_id, mode)


def _load_findings(results_dir: Path) -> list[Finding]:
    path = results_dir / "verified_findings.jsonl"
    if not path.is_file():
        return []
    findings: list[Finding] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        findings.append(Finding.model_validate(json.loads(line)))
    return findings
