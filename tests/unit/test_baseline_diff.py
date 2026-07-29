from pathlib import Path

from backend.core.baseline import (
    apply_baseline_diff,
    baseline_path,
    filter_reportable_findings,
    load_baseline,
    save_baseline,
)
from backend.core.context import Finding, FindingStatus, Severity


def _finding(rule_id: str, file: str = "a.py", line: int = 1) -> Finding:
    return Finding(
        scan_id="scan-1",
        project="demo",
        severity=Severity.HIGH,
        source="semgrep",
        rule_id=rule_id,
        file=file,
        line=line,
        message="issue",
    )


def test_apply_baseline_diff_marks_new_and_suppressed() -> None:
    current = [_finding("rule.a"), _finding("rule.b")]
    baseline = [_finding("rule.a")]
    diffed = apply_baseline_diff(current, baseline)
    by_rule = {item.rule_id: item.status for item in diffed}
    assert by_rule["rule.a"] == FindingStatus.SUPPRESSED
    assert by_rule["rule.b"] == FindingStatus.NEW


def test_filter_reportable_findings_new_only() -> None:
    findings = [
        _finding("rule.a").model_copy(update={"status": FindingStatus.SUPPRESSED}),
        _finding("rule.b").model_copy(update={"status": FindingStatus.NEW}),
    ]
    reportable = filter_reportable_findings(findings, new_only=True)
    assert len(reportable) == 1
    assert reportable[0].rule_id == "rule.b"


def test_save_and_load_baseline_roundtrip(tmp_path: Path) -> None:
    findings = [_finding("rule.a")]
    path = tmp_path / "main.json"
    save_baseline(findings, path, project="demo", branch="main")
    loaded = load_baseline(path)
    assert len(loaded) == 1
    assert loaded[0].rule_id == "rule.a"


def test_baseline_path_layout(tmp_path: Path) -> None:
    path = baseline_path(tmp_path, "novel-assistant-v3", "main")
    assert path == tmp_path / "baselines" / "novel-assistant-v3" / "main.json"
