from __future__ import annotations

from backend.core.context import Finding, FindingStatus
from backend.core.severity import Severity


def parse_fail_on(value: str | None) -> Severity | None:
    if not value or value.lower() == "none":
        return None
    mapping = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
        "info": Severity.INFO,
    }
    return mapping.get(value.lower())


def severity_rank(severity: Severity) -> int:
    order = {
        Severity.CRITICAL: 5,
        Severity.HIGH: 4,
        Severity.MEDIUM: 3,
        Severity.LOW: 2,
        Severity.INFO: 1,
    }
    return order.get(severity, 0)


def resolve_fail_on(
    *,
    cli_fail_on: str | None,
    project_fail_on: str,
) -> Severity | None:
    if cli_fail_on is not None:
        return parse_fail_on(cli_fail_on)
    return parse_fail_on(project_fail_on)


def gate_findings(
    findings: list[Finding],
    *,
    fail_on: Severity | None,
    report_mode: str,
    new_only: bool = True,
) -> tuple[list[Finding], bool]:
    candidates = findings
    if new_only:
        candidates = [f for f in findings if f.status == FindingStatus.NEW]
    if report_mode != "block" or fail_on is None:
        return candidates, False
    threshold = severity_rank(fail_on)
    failed = any(severity_rank(f.severity) >= threshold for f in candidates)
    return candidates, failed


def evaluate_exit_code(
    findings: list[Finding],
    *,
    fail_on: Severity | None,
    report_mode: str,
    new_only: bool = True,
) -> int:
    _, failed = gate_findings(
        findings,
        fail_on=fail_on,
        report_mode=report_mode,
        new_only=new_only,
    )
    return 1 if failed else 0
