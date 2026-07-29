from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from backend.core.context import Finding, ScanContext
from backend.core.registry import register_detector
from backend.core.subprocess_runner import run_command


def resolve_gitleaks_binary(repo_root: Path) -> str | None:
    env_path = os.environ.get("GITLEAKS_PATH", "").strip()
    if env_path and Path(env_path).is_file():
        return env_path
    bundled = repo_root / ".tools" / "gitleaks.exe"
    if bundled.is_file():
        return str(bundled)
    bundled_unix = repo_root / ".tools" / "gitleaks"
    if bundled_unix.is_file():
        return str(bundled_unix)
    return "gitleaks"


@register_detector("gitleaks")
class GitleaksDetector:
    id = "gitleaks"
    name = "gitleaks"
    supported_languages = ["python", "javascript", "typescript", "yaml", "json", "env"]

    def run(self, ctx: ScanContext) -> list[Finding]:
        from backend.core.path_validation import get_repo_root

        repo_root = get_repo_root()
        binary = resolve_gitleaks_binary(repo_root)
        if not binary:
            ctx.errors.append("gitleaks: binary not found")
            return []

        if not ctx.project_root.exists():
            return []

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            output_path = Path(tmp.name)

        target = ctx.project_root
        cmd = [
            binary,
            "detect",
            "--source",
            str(target),
            "--no-git",
            "--report-format",
            "json",
            "--report-path",
            str(output_path),
        ]
        result = run_command(cmd, cwd=ctx.project_root)
        if not output_path.exists() or output_path.stat().st_size == 0:
            ctx.errors.append(f"gitleaks failed: {result.stderr or result.stdout or 'empty report'}")
            output_path.unlink(missing_ok=True)
            return []

        try:
            payload = json.loads(output_path.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError as exc:
            ctx.errors.append(f"gitleaks JSON parse failed: {exc}")
            return []
        finally:
            output_path.unlink(missing_ok=True)

        items = payload if isinstance(payload, list) else payload.get("findings", [])
        return [
            Finding.from_gitleaks(item, scan_id=ctx.scan_id, project=ctx.project_config.name)
            for item in items
            if isinstance(item, dict)
        ]
