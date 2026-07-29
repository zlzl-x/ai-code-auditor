from __future__ import annotations

import json
import shutil

from backend.core.context import Finding, ScanContext
from backend.core.registry import register_detector
from backend.core.subprocess_runner import run_command


@register_detector("npm_audit")
class NpmAuditDetector:
    id = "npm_audit"
    name = "npm audit"
    supported_languages = ["javascript", "typescript"]

    def run(self, ctx: ScanContext) -> list[Finding]:
        package_json = ctx.project_root / "package.json"
        if not package_json.is_file():
            return []

        lockfile = ctx.project_root / "package-lock.json"
        pnpm_lock = ctx.project_root / "pnpm-lock.yaml"
        if pnpm_lock.is_file() and shutil.which("pnpm") is not None:
            cmd = ["pnpm", "audit", "--json"]
        elif lockfile.is_file() and shutil.which("npm") is not None:
            cmd = ["npm", "audit", "--json"]
        elif shutil.which("npm") is not None:
            cmd = ["npm", "audit", "--json"]
        else:
            ctx.errors.append("npm_audit: npm/pnpm not found in PATH")
            return []

        try:
            result = run_command(cmd, cwd=ctx.project_root, timeout=180)
        except FileNotFoundError:
            ctx.errors.append("npm_audit: package manager not found in PATH")
            return []
        if not result.stdout.strip():
            if result.timed_out:
                ctx.errors.append("npm_audit: timed out")
            return []

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            ctx.errors.append(f"npm_audit JSON parse failed: {exc}")
            return []

        findings: list[Finding] = []
        vulnerabilities = payload.get("vulnerabilities", {})
        for package, vuln in vulnerabilities.items():
            if not isinstance(vuln, dict):
                continue
            findings.append(
                Finding.from_npm_audit(
                    package,
                    vuln,
                    scan_id=ctx.scan_id,
                    project=ctx.project_config.name,
                )
            )
        return findings
