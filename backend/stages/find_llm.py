from __future__ import annotations

import json
from pathlib import Path

from backend.core.context import Finding, ScanContext, Severity
from backend.core.llm import get_llm_client
from backend.core.llm.models import resolve_llm_model
from backend.core.llm.structured import complete_json
from backend.core.llm.file_filter import read_file_snippet
from backend.core.registry import load_modules_config, register_stage
from backend.prompts.find_prompt import FIND_SYSTEM_PROMPT, build_find_user_prompt
from backend.prompts.untrusted import make_nonce


@register_stage("find_llm")
class FindLLMStage:
    id = "find_llm"

    def run(self, ctx: ScanContext) -> ScanContext:
        if ctx.mode != "deep":
            return ctx

        from backend.core.path_validation import get_repo_root

        config = load_modules_config(get_repo_root())
        llm_config = config.get("llm", {})
        model = resolve_llm_model("screening")
        max_findings = int(llm_config.get("max_findings_per_scan", 20))

        client = get_llm_client(model, role="screening")
        new_findings: list[Finding] = []

        for area in ctx.project_config.focus_areas:
            target = (ctx.project_root / area.path).resolve()
            if not target.exists():
                continue
            paths = [target] if target.is_file() else list(target.rglob("*"))
            for path in paths:
                if not path.is_file():
                    continue
                snippet = read_file_snippet(path)
                if snippet is None:
                    continue
                nonce = make_nonce()
                rel = str(path.relative_to(ctx.project_root))
                user_prompt = build_find_user_prompt(
                    file_path=rel,
                    snippet=snippet,
                    nonce=nonce,
                )
                try:
                    payload, response = complete_json(
                        client,
                        role="screening",
                        model=model,
                        system=FIND_SYSTEM_PROMPT,
                        user=user_prompt,
                        max_tokens=2048,
                    )
                except json.JSONDecodeError:
                    ctx.errors.append(f"find_llm: invalid JSON for {rel}")
                    continue

                ctx.scan_meta.tokens_in += response.tokens_in
                ctx.scan_meta.tokens_out += response.tokens_out
                if response.model not in ctx.scan_meta.models_used:
                    ctx.scan_meta.models_used.append(response.model)

                for item in payload.get("findings", []):
                    severity_raw = str(item.get("severity", "medium")).lower()
                    try:
                        severity = Severity(severity_raw)
                    except ValueError:
                        severity = Severity.MEDIUM
                    new_findings.append(
                        Finding(
                            scan_id=ctx.scan_id,
                            project=ctx.project_config.name,
                            severity=severity,
                            confidence=float(item.get("confidence", 0.7)),
                            source="llm_find",
                            rule_id=str(item.get("rule_id", "llm.unknown")),
                            file=rel,
                            line=int(item.get("line", 0)),
                            message=str(item.get("message", "")),
                            evidence=str(item.get("evidence", "")),
                            cwe=str(item.get("cwe", "")),
                            remediation=str(item.get("remediation", "")),
                        )
                    )
                    if len(new_findings) >= max_findings:
                        break
            if len(new_findings) >= max_findings:
                break

        ctx.findings.extend(new_findings)
        return ctx
