from backend.core.context import Finding, ProjectConfig, ScanContext, Severity
from backend.reporters.pr_comment import build_pr_comment


def test_pr_comment_is_markdown_without_html() -> None:
    finding = Finding(
        scan_id="scan-1",
        project="demo",
        severity=Severity.HIGH,
        source="semgrep",
        rule_id="rule|pipe",
        file="app/main.py",
        line=9,
        message="<script>alert(1)</script>",
    )
    ctx = ScanContext(
        scan_id="scan-1",
        project_config=ProjectConfig(name="demo", path=".", languages=["python"]),
        project_root=__import__("pathlib").Path("."),
        results_dir=__import__("pathlib").Path("."),
        findings=[finding],
        verified_findings=[finding],
    )
    comment = build_pr_comment(ctx, new_only=False)
    assert "## Security Audit Summary" in comment
    assert "<script>" not in comment
    assert "rule\\|pipe" in comment or "rule|pipe" in comment
