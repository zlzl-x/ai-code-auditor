from backend.core.context import Finding, Severity


def test_finding_from_semgrep_maps_severity() -> None:
    item = {
        "check_id": "javascript.lang.security.audit.spawn-shell-true.spawn-shell-true",
        "path": "app/main.js",
        "start": {"line": 10},
        "extra": {
            "message": "spawn shell true",
            "severity": "ERROR",
            "lines": "spawn(..., {shell: true})",
            "metadata": {"cwe": ["CWE-78"]},
        },
    }
    finding = Finding.from_semgrep(item, scan_id="scan-1", project="demo")
    assert finding.severity == Severity.HIGH
    assert finding.source == "semgrep"
    assert finding.rule_id.endswith("spawn-shell-true")


def test_finding_from_bandit_maps_severity() -> None:
    item = {
        "test_id": "B101",
        "filename": "app.py",
        "line_number": 3,
        "issue_text": "Test issue",
        "issue_severity": "MEDIUM",
        "code": "pass",
        "issue_cwe": {"id": 78},
    }
    finding = Finding.from_bandit(item, scan_id="scan-1", project="demo")
    assert finding.severity == Severity.MEDIUM
    assert finding.cwe == "CWE-78"
