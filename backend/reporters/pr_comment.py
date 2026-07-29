from __future__ import annotations

import re

from backend.core.baseline import filter_reportable_findings
from backend.core.context import ScanContext, Severity


def escape_markdown(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|])", r"\\\1", text)


def build_pr_comment(ctx: ScanContext, *, new_only: bool = True, limit: int = 20) -> str:
    all_findings = ctx.verified_findings or ctx.findings
    findings = filter_reportable_findings(all_findings, new_only=new_only)
    counts = {severity.value: 0 for severity in Severity}
    for finding in findings:
        counts[finding.severity.value] = counts.get(finding.severity.value, 0) + 1

    lines = [
        "## Security Audit Summary",
        "",
        f"- Project: `{escape_markdown(ctx.project_config.name)}`",
        f"- Mode: `{escape_markdown(ctx.mode)}`",
        f"- New findings: **{len(findings)}**",
        f"- Total after triage: **{len(all_findings)}**",
        "",
        "### Severity (reported)",
    ]
    for severity in ("critical", "high", "medium", "low", "info"):
        if counts.get(severity):
            lines.append(f"- **{severity}**: {counts[severity]}")

    lines.extend(["", "### Top Findings", ""])
    if not findings:
        lines.append("_No new findings._")
    else:
        lines.append("| Severity | Rule | Location |")
        lines.append("| --- | --- | --- |")
        for finding in findings[:limit]:
            location = f"{escape_markdown(finding.file)}:{finding.line}"
            lines.append(
                f"| {finding.severity.value} | "
                f"`{escape_markdown(finding.rule_id)}` | {location} |"
            )

    return "\n".join(lines) + "\n"


def write_pr_comment(
    ctx: ScanContext,
    output_path,
    *,
    new_only: bool = True,
) -> None:
    from pathlib import Path

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_pr_comment(ctx, new_only=new_only), encoding="utf-8")
