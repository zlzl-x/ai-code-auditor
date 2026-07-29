from __future__ import annotations

import json
import shutil

from backend.core.context import Finding, ScanContext
from backend.core.registry import register_detector
from backend.core.subprocess_runner import run_command


@register_detector("config_audit")
class ConfigAuditDetector:
    id = "config_audit"
    name = "Agent Config Audit"
    supported_languages = []

    def run(self, ctx: ScanContext) -> list[Finding]:
        if not self._should_run(ctx):
            return []

        if shutil.which("npx") is None:
            ctx.errors.append("config_audit: npx not found in PATH")
            return []

        cmd = [
            "npx",
            "ecc-agentshield",
            "scan",
            "--path",
            str(ctx.project_root),
            "--format",
            "json",
            "--min-severity",
            "medium",
        ]
        result = run_command(cmd, cwd=ctx.project_root, timeout=120)
        raw = result.stdout.strip()
        if not raw:
            ctx.errors.append(f"config_audit failed: {result.stderr or 'no output'}")
            return []

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            ctx.errors.append(f"config_audit JSON parse failed: {exc}")
            return []

        items = payload.get("findings", payload.get("issues", []))
        if isinstance(payload, list):
            items = payload
        return [
            Finding.from_agentshield(item, scan_id=ctx.scan_id, project=ctx.project_config.name)
            for item in items
            if isinstance(item, dict)
        ]

    @staticmethod
    def _should_run(ctx: ScanContext) -> bool:
        root = ctx.project_root
        return (root / ".cursor").exists() or (root / ".claude").exists()
