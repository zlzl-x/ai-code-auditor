from __future__ import annotations

import json
from pathlib import Path

from backend.core.baseline import filter_reportable_findings
from backend.core.context import ScanContext, Severity
from backend.core.registry import register_reporter


def _severity_to_level(severity: Severity) -> str:
    if severity in {Severity.CRITICAL, Severity.HIGH}:
        return "error"
    if severity == Severity.MEDIUM:
        return "warning"
    return "note"


def _build_rules(findings) -> list[dict]:
    seen: dict[str, dict] = {}
    for finding in findings:
        if finding.rule_id in seen:
            continue
        seen[finding.rule_id] = {
            "id": finding.rule_id,
            "name": finding.rule_id,
            "shortDescription": {"text": finding.message[:200]},
            "defaultConfiguration": {"level": _severity_to_level(finding.severity)},
        }
    return list(seen.values())


def build_sarif_document(ctx: ScanContext, *, new_only: bool = True) -> dict:
    findings = filter_reportable_findings(
        ctx.verified_findings or ctx.findings,
        new_only=new_only,
    )
    results = []
    for finding in findings:
        result = {
            "ruleId": finding.rule_id,
            "level": _severity_to_level(finding.severity),
            "message": {"text": finding.message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": finding.file},
                        "region": {"startLine": max(finding.line, 1)},
                    }
                }
            ],
            "properties": {
                "source": finding.source,
                "cwe": finding.cwe,
                "verified": finding.verified,
                "status": finding.status.value,
            },
        }
        results.append(result)

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ai-code-auditor",
                        "informationUri": "https://github.com/",
                        "rules": _build_rules(findings),
                    }
                },
                "results": results,
            }
        ],
    }


@register_reporter("sarif")
class SarifReporter:
    id = "sarif"

    def write(self, ctx: ScanContext, *, new_only: bool = True, output_path: Path | None = None) -> Path:
        document = build_sarif_document(ctx, new_only=new_only)
        target = output_path or (ctx.results_dir / "audit.sarif")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
        return target
