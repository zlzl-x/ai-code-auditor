from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from backend.core.context import Finding, FindingStatus


def finding_fingerprint(finding: Finding) -> tuple[str, str, int]:
    return (finding.rule_id, finding.file, finding.line)


def baseline_path(repo_root: Path, project_id: str, branch: str) -> Path:
    return repo_root / "baselines" / project_id / f"{branch}.json"


def resolve_baseline_path(
    repo_root: Path,
    project_id: str,
    baseline: str,
) -> Path | None:
    candidate = Path(baseline)
    if candidate.is_file():
        return candidate.resolve()
    return baseline_path(repo_root, project_id, baseline)


def load_baseline(path: Path) -> list[Finding]:
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [Finding.model_validate(item) for item in raw]
    findings = raw.get("findings", [])
    return [Finding.model_validate(item) for item in findings]


def save_baseline(
    findings: Iterable[Finding],
    path: Path,
    *,
    project: str = "",
    branch: str = "",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "project": project,
        "branch": branch,
        "findings": [finding.model_dump(mode="json") for finding in findings],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def apply_baseline_diff(
    findings: list[Finding],
    baseline_findings: list[Finding],
) -> list[Finding]:
    baseline_keys = {finding_fingerprint(item) for item in baseline_findings}
    updated: list[Finding] = []
    for finding in findings:
        key = finding_fingerprint(finding)
        if key in baseline_keys:
            updated.append(finding.model_copy(update={"status": FindingStatus.SUPPRESSED}))
        else:
            updated.append(finding.model_copy(update={"status": FindingStatus.NEW}))
    return updated


def filter_reportable_findings(
    findings: list[Finding],
    *,
    new_only: bool = True,
) -> list[Finding]:
    if not new_only:
        return list(findings)
    return [finding for finding in findings if finding.status == FindingStatus.NEW]
