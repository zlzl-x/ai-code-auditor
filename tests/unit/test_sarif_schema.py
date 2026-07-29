import json

from backend.core.context import Finding, ProjectConfig, ScanContext, Severity
from backend.reporters.sarif import SarifReporter, build_sarif_document


def _ctx(findings: list[Finding]) -> ScanContext:
    return ScanContext(
        scan_id="scan-1",
        project_config=ProjectConfig(name="demo", path=".", languages=["python"]),
        project_root=__import__("pathlib").Path("."),
        results_dir=__import__("pathlib").Path("."),
        findings=findings,
        verified_findings=findings,
    )


def test_sarif_schema_valid(tmp_path) -> None:
    finding = Finding(
        scan_id="scan-1",
        project="demo",
        severity=Severity.HIGH,
        source="semgrep",
        rule_id="python.lang.security.audit",
        file="app/main.py",
        line=10,
        message="Potential issue",
    )
    ctx = _ctx([finding])
    ctx.results_dir = tmp_path
    SarifReporter().write(ctx)
    document = json.loads((tmp_path / "audit.sarif").read_text(encoding="utf-8"))
    assert document["version"] == "2.1.0"
    assert document["$schema"].endswith("sarif-2.1.0.json")
    run = document["runs"][0]
    assert run["tool"]["driver"]["name"] == "ai-code-auditor"
    assert run["results"][0]["ruleId"] == "python.lang.security.audit"


def test_build_sarif_document_has_rules() -> None:
    finding = Finding(
        scan_id="scan-1",
        project="demo",
        severity=Severity.MEDIUM,
        source="bandit",
        rule_id="bandit.B101",
        file="a.py",
        line=3,
        message="test",
    )
    document = build_sarif_document(_ctx([finding]))
    assert document["runs"][0]["tool"]["driver"]["rules"][0]["id"] == "bandit.B101"
