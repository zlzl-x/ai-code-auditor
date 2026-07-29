from __future__ import annotations

import html
from pathlib import Path

from backend.core.context import ScanContext, Severity
from backend.core.registry import register_reporter


@register_reporter("markdown")
class MarkdownReporter:
    id = "markdown"

    def write(self, ctx: ScanContext) -> Path:
        findings = ctx.verified_findings or ctx.findings
        lines: list[str] = [
            f"# Security Audit Report: {html.escape(ctx.project_config.name)}",
            "",
            "## Summary",
            "",
            f"- Scan ID: `{ctx.scan_id}`",
            f"- Mode: `{ctx.mode}`",
            f"- Total findings (after triage): {len(findings)}",
        ]

        triage = ctx.triage_summary
        if triage:
            lines.extend(
                [
                    f"- Raw count: {triage.get('total', 'N/A')}",
                    f"- Deduped count: {triage.get('deduped', 'N/A')}",
                ]
            )

        meta = ctx.scan_meta
        if meta.tokens_in or meta.tokens_out:
            lines.extend(
                [
                    f"- Tokens in: {meta.tokens_in}",
                    f"- Tokens out: {meta.tokens_out}",
                    f"- Models: {', '.join(meta.models_used) or 'none'}",
                ]
            )

        lines.extend(["", "## Severity Distribution", ""])
        counts: dict[str, int] = {}
        for finding in findings:
            key = finding.severity.value
            counts[key] = counts.get(key, 0) + 1
        for severity in ("critical", "high", "medium", "low", "info"):
            if counts.get(severity):
                lines.append(f"- **{severity}**: {counts[severity]}")

        critical_high = [
            f
            for f in findings
            if f.severity in {Severity.CRITICAL, Severity.HIGH}
        ]
        lines.extend(["", "## Critical / High Findings", ""])
        if not critical_high:
            lines.append("_None_")
        else:
            for finding in critical_high:
                lines.extend(_format_finding(finding))

        unverified = [f for f in findings if not f.verified]
        lines.extend(["", "## Unverified Findings", ""])
        if not unverified:
            lines.append("_None_")
        else:
            for finding in unverified[:20]:
                lines.extend(_format_finding(finding, brief=True))

        sandbox_findings = [f for f in findings if f.sandbox_note]
        lines.extend(["", "## Sandbox Verification", ""])
        if not sandbox_findings:
            lines.append("_Not run (enable with --enable-sandbox)._")
        else:
            for finding in sandbox_findings[:20]:
                lines.append(
                    f"- `{html.escape(finding.rule_id)}` "
                    f"({html.escape(finding.file)}:{finding.line}): "
                    f"{html.escape(finding.sandbox_note)}"
                )

        lines.extend(["", "## Remediation Notes", ""])
        remediations = [f for f in findings if f.remediation]
        if not remediations:
            lines.append("_See individual findings for guidance._")
        else:
            for finding in remediations[:10]:
                lines.append(
                    f"- `{html.escape(finding.rule_id)}` "
                    f"({html.escape(finding.file)}): "
                    f"{html.escape(finding.remediation)}"
                )

        output_path = ctx.results_dir / "AUDIT_REPORT.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return output_path


def _format_finding(finding, *, brief: bool = False) -> list[str]:
    verified = "yes" if finding.verified else "no"
    lines = [
        "",
        f"### {html.escape(finding.rule_id)} — {html.escape(finding.severity.value)}",
        "",
        f"- File: `{html.escape(finding.file)}:{finding.line}`",
        f"- Source: {html.escape(finding.source)}",
        f"- Verified: {verified}",
        f"- Message: {html.escape(finding.message)}",
    ]
    if finding.verify_note:
        lines.append(f"- Verify note: {html.escape(finding.verify_note)}")
    if not brief and finding.evidence:
        lines.extend(
            [
                "",
                "```",
                finding.evidence,
                "```",
            ]
        )
    return lines
