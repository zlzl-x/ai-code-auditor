from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from backend.core.context import Finding, ScanContext
from backend.core.registry import register_detector
from backend.core.subprocess_runner import run_command

SECURITY_RULE_PREFIXES = ("security/", "no-eval", "no-implied-eval", "detect-")


@register_detector("eslint_security")
class EslintSecurityDetector:
    id = "eslint_security"
    name = "ESLint Security"
    supported_languages = ["javascript", "typescript"]

    def run(self, ctx: ScanContext) -> list[Finding]:
        if shutil.which("npx") is None:
            ctx.errors.append("eslint_security: npx not found in PATH")
            return []

        targets = self._resolve_targets(ctx)
        if not targets:
            return []

        has_config = any(
            (ctx.project_root / name).exists()
            for name in ("eslint.config.js", "eslint.config.mjs", ".eslintrc", ".eslintrc.json", ".eslintrc.js")
        )
        if not has_config and not (ctx.project_root / "node_modules").is_dir():
            ctx.errors.append("eslint_security: skipped (no eslint config or node_modules)")
            return []

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            output_path = Path(tmp.name)

        cmd = [
            "npx",
            "eslint",
            "--format",
            "json",
            "--no-error-on-unmatched-pattern",
            "-o",
            str(output_path),
            *[str(path) for path in targets],
        ]
        run_command(cmd, cwd=ctx.project_root, timeout=180)
        if not output_path.exists():
            return []

        try:
            payload = json.loads(output_path.read_bytes().decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            return []
        finally:
            output_path.unlink(missing_ok=True)

        findings: list[Finding] = []
        for file_report in payload:
            for message in file_report.get("messages", []):
                rule_id = str(message.get("ruleId", ""))
                if not rule_id or not self._is_security_rule(rule_id):
                    continue
                item = {
                    **message,
                    "filePath": file_report.get("filePath", ""),
                }
                findings.append(
                    Finding.from_eslint(
                        item,
                        scan_id=ctx.scan_id,
                        project=ctx.project_config.name,
                    )
                )
        return findings

    @staticmethod
    def _is_security_rule(rule_id: str) -> bool:
        lowered = rule_id.lower()
        return any(lowered.startswith(prefix) or prefix in lowered for prefix in SECURITY_RULE_PREFIXES)

    def _resolve_targets(self, ctx: ScanContext) -> list[Path]:
        extensions = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
        paths: list[Path] = []
        if ctx.project_config.focus_areas:
            for area in ctx.project_config.focus_areas:
                target = (ctx.project_root / area.path).resolve()
                if target.is_file() and target.suffix.lower() in extensions:
                    paths.append(target)
                elif target.is_dir():
                    paths.extend(
                        path
                        for path in target.rglob("*")
                        if path.is_file() and path.suffix.lower() in extensions
                    )
            return paths
        return [ctx.project_root]
