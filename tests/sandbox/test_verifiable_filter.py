from backend.core.context import Finding, Severity
from backend.sandbox.verifiable import build_poc_command, is_verifiable, max_sandbox_pocs


def _finding(**overrides) -> Finding:
    base = {
        "scan_id": "scan-1",
        "project": "demo",
        "severity": Severity.HIGH,
        "source": "semgrep",
        "rule_id": "python.lang.security.audit.spawn-shell-true",
        "file": "app.py",
        "line": 10,
        "message": "subprocess with shell true",
        "verified": True,
        "cwe": "CWE-78",
    }
    base.update(overrides)
    return Finding(**base)


def test_is_verifiable_requires_verified_high_severity() -> None:
    assert is_verifiable(_finding())
    assert not is_verifiable(_finding(verified=False))
    assert not is_verifiable(_finding(severity=Severity.MEDIUM))


def test_build_poc_command_for_subprocess() -> None:
    command = build_poc_command(_finding())
    assert command is not None
    assert "subprocess" in " ".join(command)


def test_max_sandbox_pocs_default() -> None:
    assert max_sandbox_pocs() >= 1
