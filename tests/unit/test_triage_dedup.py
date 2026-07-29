from backend.core.context import Finding, Severity
from backend.stages.triage import TriageStage, _merge_similar_messages


def _finding(rule_id: str, file: str, line: int, severity: Severity, message: str) -> Finding:
    return Finding(
        scan_id="s1",
        project="demo",
        severity=severity,
        source="semgrep",
        rule_id=rule_id,
        file=file,
        line=line,
        message=message,
    )


def test_triage_dedup_keeps_highest_severity() -> None:
    from backend.core.context import ScanContext, ProjectConfig
    from pathlib import Path

    ctx = ScanContext(
        scan_id="s1",
        project_config=ProjectConfig(name="demo", path="."),
        project_root=Path("."),
        results_dir=Path("."),
        verified_findings=[
            _finding("r1", "a.py", 10, Severity.MEDIUM, "issue"),
            _finding("r1", "a.py", 10, Severity.HIGH, "issue"),
        ],
    )
    ctx = TriageStage().run(ctx)
    assert ctx.triage_summary["deduped"] == 1
    assert ctx.verified_findings[0].severity == Severity.HIGH


def test_merge_similar_messages() -> None:
    message = " ".join(f"token{i}" for i in range(12))
    items = [
        _finding("r1", "a.py", 1, Severity.LOW, message + " extra-a"),
        _finding("r2", "b.py", 2, Severity.HIGH, message + " extra-b"),
    ]
    merged = _merge_similar_messages(items)
    assert len(merged) == 1
    assert merged[0].severity == Severity.HIGH
