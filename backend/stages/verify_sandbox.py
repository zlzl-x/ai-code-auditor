from __future__ import annotations

from pathlib import Path

from backend.core.context import ScanContext
from backend.core.registry import register_stage
from backend.sandbox.runner import SandboxRunner
from backend.sandbox.verifiable import build_poc_command, is_verifiable, max_sandbox_pocs


@register_stage("verify_sandbox")
class VerifySandboxStage:
    id = "verify_sandbox"

    def run(self, ctx: ScanContext) -> ScanContext:
        if not ctx.enable_sandbox:
            return ctx

        if not SandboxRunner.is_available():
            ctx.errors.append("verify_sandbox: docker not available")
            return ctx

        runner = SandboxRunner()
        source_findings = list(ctx.verified_findings or ctx.findings)
        candidates = [finding for finding in source_findings if is_verifiable(finding)]
        candidates = candidates[: max_sandbox_pocs()]

        results: list[dict] = []
        updated_findings: list = []

        for finding in source_findings:
            if finding not in candidates:
                updated_findings.append(finding)
                continue

            poc_command = build_poc_command(finding)
            if not poc_command:
                updated_findings.append(
                    finding.model_copy(update={"sandbox_note": "skipped"})
                )
                continue

            target = Path(finding.file)
            if not target.is_absolute():
                target = ctx.project_root / finding.file
            snapshot = runner.create_snapshot(target if target.exists() else ctx.project_root)
            outcome = None
            try:
                outcome = runner.run_poc(poc_command, snapshot)
            finally:
                if outcome is not None:
                    runner.cleanup(outcome.container_id)

            assert outcome is not None

            note = "poc_confirmed" if outcome.exit_code == 0 and not outcome.timed_out else "poc_not_reproduced"
            updated = finding.model_copy(
                update={
                    "sandbox_verified": outcome.exit_code == 0 and not outcome.timed_out,
                    "sandbox_note": note,
                }
            )
            updated_findings.append(updated)
            results.append(
                {
                    "finding_id": finding.id,
                    "rule_id": finding.rule_id,
                    "file": finding.file,
                    "line": finding.line,
                    "sandbox_note": note,
                    "exit_code": outcome.exit_code,
                    "timed_out": outcome.timed_out,
                    "stdout": outcome.stdout[:500],
                    "stderr": outcome.stderr[:500],
                }
            )

        ctx.verified_findings = updated_findings
        ctx.sandbox_results = {
            "enabled": True,
            "attempted": len(candidates),
            "results": results,
        }
        return ctx
