from __future__ import annotations

import json
import tempfile
from pathlib import Path

from backend.core.context import Finding, ScanContext
from backend.core.registry import register_detector
from backend.core.subprocess_runner import run_command


@register_detector("semgrep")
class SemgrepDetector:
    id = "semgrep"
    name = "Semgrep"
    supported_languages = [
        "python",
        "javascript",
        "typescript",
        "yaml",
        "json",
        "html",
    ]

    def run(self, ctx: ScanContext) -> list[Finding]:
        targets = self._resolve_targets(ctx)
        if not targets:
            ctx.errors.append("semgrep: no scan targets found")
            return []

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            output_path = Path(tmp.name)

        cmd = ["semgrep", "--config", "auto", "--json", "-o", str(output_path)]
        repo_root = _find_repo_root()
        for ruleset in ("python", "javascript", "ai-app"):
            rules_path = repo_root / "rules" / ruleset
            if rules_path.is_dir():
                cmd.extend(["--config", str(rules_path)])
        for name in ("node_modules", "dist", ".git", ".venv"):
            cmd.extend(["--exclude", name])
        cmd.extend(str(path) for path in targets)

        result = run_command(cmd, cwd=ctx.project_root)
        if not output_path.exists():
            ctx.errors.append(f"semgrep failed: {result.stderr or result.stdout}")
            return []

        raw_text = output_path.read_bytes().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            ctx.errors.append(f"semgrep JSON parse failed: {exc}")
            return []
        finally:
            output_path.unlink(missing_ok=True)
        return [
            Finding.from_semgrep(item, scan_id=ctx.scan_id, project=ctx.project_config.name)
            for item in payload.get("results", [])
        ]

    def _resolve_targets(self, ctx: ScanContext) -> list[Path]:
        if ctx.project_config.focus_areas:
            targets = []
            for area in ctx.project_config.focus_areas:
                target = (ctx.project_root / area.path).resolve()
                if target.exists():
                    targets.append(target)
            return targets
        return [ctx.project_root]


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "modules.yaml").is_file():
            return parent
    return current.parents[2]
