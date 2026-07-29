from __future__ import annotations

import json
import tempfile
from pathlib import Path

from backend.core.context import Finding, ScanContext
from backend.core.registry import register_detector
from backend.core.subprocess_runner import run_command


@register_detector("bandit")
class BanditDetector:
    id = "bandit"
    name = "Bandit"
    supported_languages = ["python"]

    def run(self, ctx: ScanContext) -> list[Finding]:
        targets = self._resolve_targets(ctx)
        if not targets:
            return []

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            output_path = Path(tmp.name)

        cmd = ["bandit", "-r", *[str(path) for path in targets], "-f", "json", "-o", str(output_path)]
        result = run_command(cmd, cwd=ctx.project_root)
        if not output_path.exists():
            if result.timed_out:
                ctx.errors.append("bandit timed out")
            return []

        raw_text = output_path.read_bytes().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            ctx.errors.append(f"bandit JSON parse failed: {exc}")
            return []
        finally:
            output_path.unlink(missing_ok=True)
        return [
            Finding.from_bandit(item, scan_id=ctx.scan_id, project=ctx.project_config.name)
            for item in payload.get("results", [])
        ]

    def _resolve_targets(self, ctx: ScanContext) -> list[Path]:
        candidates: list[Path] = []
        skills_dir = ctx.project_root / ".cursor" / "skills"
        if skills_dir.exists():
            candidates.append(skills_dir)
        if candidates:
            return candidates
        return []
