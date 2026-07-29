from pathlib import Path

from backend.core.context import Finding, ProjectConfig, ScanContext, Severity
from backend.reporters.markdown import MarkdownReporter


def test_markdown_report_sections(tmp_path: Path) -> None:
    ctx = ScanContext(
        scan_id="scan-1",
        project_config=ProjectConfig(name="demo-app", path="."),
        project_root=tmp_path,
        results_dir=tmp_path / "results",
        mode="quick",
        verified_findings=[
            Finding(
                scan_id="scan-1",
                project="demo-app",
                severity=Severity.HIGH,
                verified=True,
                source="semgrep",
                rule_id="rule.high",
                file="app.js",
                line=10,
                message="High issue",
                evidence="exec(cmd)",
            )
        ],
        triage_summary={"total": 1, "deduped": 1, "by_severity": {"high": 1}},
        scan_meta=__import__("backend.core.context", fromlist=["ScanMeta"]).ScanMeta(
            tokens_in=100,
            tokens_out=50,
            models_used=["mock"],
        ),
    )
    output = MarkdownReporter().write(ctx)
    text = output.read_text(encoding="utf-8")
    assert "# Security Audit Report" in text
    assert "## Summary" in text
    assert "## Severity Distribution" in text
    assert "## Critical / High Findings" in text
    assert "## Unverified Findings" in text
    assert "## Remediation Notes" in text
