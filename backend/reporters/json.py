from __future__ import annotations

import json
from pathlib import Path

from backend.core.baseline import filter_reportable_findings
from backend.core.context import ScanContext
from backend.core.registry import register_reporter


@register_reporter("json")
class JsonReporter:
    id = "json"

    def write(
        self,
        ctx: ScanContext,
        *,
        new_only: bool = True,
        include_evidence: bool = False,
        output_path: Path | None = None,
    ) -> Path:
        findings = filter_reportable_findings(
            ctx.verified_findings or ctx.findings,
            new_only=new_only,
        )
        rows = []
        for finding in findings:
            data = finding.model_dump(mode="json")
            if not include_evidence:
                data["evidence"] = ""
            rows.append(data)

        payload = {
            "scan_id": ctx.scan_id,
            "project": ctx.project_config.name,
            "mode": ctx.mode,
            "finding_count": len(rows),
            "findings": rows,
        }
        target = output_path or (ctx.results_dir / "findings.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return target
