from backend.core.context import Finding, Severity
from backend.sandbox.verifiable import build_poc_command, is_verifiable


def _finding(rule_id: str, message: str, cwe: str = "") -> Finding:
    return Finding(
        scan_id="scan-1",
        project="demo",
        severity=Severity.HIGH,
        source="semgrep",
        rule_id=rule_id,
        file="a.py",
        line=1,
        message=message,
        verified=True,
        cwe=cwe,
    )


def test_build_poc_command_variants() -> None:
    assert "subprocess" in " ".join(build_poc_command(_finding("r", "subprocess shell")) or [])
    assert build_poc_command(_finding("r", "sql injection", "CWE-89"))
    assert build_poc_command(_finding("r", "path traversal issue", "CWE-22"))
    assert build_poc_command(_finding("r", "pickle load", "CWE-502"))


def test_is_verifiable_by_keyword_without_cwe() -> None:
    assert is_verifiable(_finding("bandit.B602", "subprocess call with shell=True"))
