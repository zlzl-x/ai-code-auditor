import json

from backend.core.context import Finding, ProjectConfig, ScanContext, Severity
from backend.reporters.sarif import SarifReporter


def test_sarif_escape_malicious_message(tmp_path) -> None:
    finding = Finding(
        scan_id="scan-1",
        project="demo",
        severity=Severity.HIGH,
        source="semgrep",
        rule_id='evil"}',
        file="a.py",
        line=1,
        message='"}</script><script>alert(1)</script>',
        evidence="secret-token-should-not-appear",
    )
    ctx = ScanContext(
        scan_id="scan-1",
        project_config=ProjectConfig(name="demo", path=".", languages=["python"]),
        project_root=tmp_path,
        results_dir=tmp_path,
        findings=[finding],
        verified_findings=[finding],
    )
    SarifReporter().write(ctx)
    raw = (tmp_path / "audit.sarif").read_text(encoding="utf-8")
    payload = json.loads(raw)
    assert "secret-token-should-not-appear" not in raw
    message = payload["runs"][0]["results"][0]["message"]["text"]
    assert "<script>" in message
