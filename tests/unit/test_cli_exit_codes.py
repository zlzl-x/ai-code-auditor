from backend.core.context import Finding, FindingStatus, Severity
from backend.core.scan_gate import evaluate_exit_code, gate_findings, parse_fail_on


def _finding(severity: Severity, *, status: FindingStatus = FindingStatus.NEW) -> Finding:
    return Finding(
        scan_id="scan-1",
        project="demo",
        severity=severity,
        source="semgrep",
        rule_id="test.rule",
        file="a.py",
        line=1,
        message="issue",
        status=status,
    )


def test_report_only_always_exits_zero() -> None:
    findings = [_finding(Severity.CRITICAL)]
    assert evaluate_exit_code(findings, fail_on=Severity.CRITICAL, report_mode="report_only") == 0


def test_block_critical_exits_one() -> None:
    findings = [_finding(Severity.CRITICAL)]
    assert evaluate_exit_code(findings, fail_on=Severity.CRITICAL, report_mode="block") == 1


def test_block_ignores_suppressed_findings() -> None:
    findings = [_finding(Severity.CRITICAL, status=FindingStatus.SUPPRESSED)]
    assert evaluate_exit_code(findings, fail_on=Severity.CRITICAL, report_mode="block") == 0


def test_gate_findings_high_threshold() -> None:
    findings = [_finding(Severity.MEDIUM)]
    gated, failed = gate_findings(findings, fail_on=Severity.HIGH, report_mode="block")
    assert gated
    assert failed is False


def test_parse_fail_on_none() -> None:
    assert parse_fail_on("none") is None
    assert parse_fail_on("critical") == Severity.CRITICAL
