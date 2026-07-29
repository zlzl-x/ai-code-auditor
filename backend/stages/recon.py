from __future__ import annotations

from collections import Counter
from pathlib import Path

from backend.core.context import ScanContext
from backend.core.registry import register_stage
from backend.stages.threat_model import build_threat_model


LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".html": "html",
}


@register_stage("recon")
class ReconStage:
    id = "recon"

    def run(self, ctx: ScanContext) -> ScanContext:
        root = ctx.project_root
        languages = Counter()
        file_count = 0
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in {"node_modules", ".git", "dist", ".venv"} for part in path.parts):
                continue
            file_count += 1
            lang = LANGUAGE_EXTENSIONS.get(path.suffix.lower())
            if lang:
                languages[lang] += 1

        focus_status = []
        for area in ctx.project_config.focus_areas:
            focus_path = root / area.path
            focus_status.append(
                {
                    "path": area.path,
                    "description": area.description,
                    "exists": focus_path.exists(),
                }
            )

        entry_points = []
        for marker in ["package.json", "apps", "src/main", "pyproject.toml"]:
            marker_path = root / marker
            if marker_path.exists():
                entry_points.append(marker)

        ctx.recon_data = {
            "project": ctx.project_config.name,
            "languages": dict(languages),
            "file_count": file_count,
            "focus_areas": focus_status,
            "entry_points": entry_points,
            "configured_languages": ctx.project_config.languages,
        }
        ctx.threat_model_md = build_threat_model(ctx)
        return ctx
