from __future__ import annotations

from pathlib import Path
import yaml

from backend.core.context import FocusArea, ProjectConfig

PROJECTS_DIR_NAME = "projects"


class PathValidationError(ValueError):
    """Raised when a project path fails validation."""


def get_repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / PROJECTS_DIR_NAME).is_dir():
            return candidate
    raise PathValidationError("Could not locate repository root")


def load_project_config(project_id: str, repo_root: Path | None = None) -> ProjectConfig:
    root = repo_root or get_repo_root()
    config_path = root / PROJECTS_DIR_NAME / project_id / "config.yaml"
    if not config_path.is_file():
        raise PathValidationError(f"Project config not found: {project_id}")
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    focus_areas = [
        FocusArea(**area) if isinstance(area, dict) else FocusArea(path=str(area))
        for area in data.get("focus_areas", [])
    ]
    return ProjectConfig(
        name=data.get("name", project_id),
        path=data["path"],
        languages=list(data.get("languages", [])),
        exclude=list(data.get("exclude", [])),
        scan_mode=data.get("scan_mode", "quick"),
        fail_on=data.get("fail_on", "critical"),
        focus_areas=focus_areas,
    )


def resolve_project_root(config: ProjectConfig) -> Path:
    raw_path = config.path
    if ".." in Path(raw_path).parts:
        raise PathValidationError("Project path must not contain '..'")
    resolved = Path(raw_path).expanduser().resolve()
    if not resolved.exists():
        raise PathValidationError(f"Project path does not exist: {resolved}")
    if not resolved.is_dir():
        raise PathValidationError(f"Project path is not a directory: {resolved}")
    return resolved


def ensure_child_path(project_root: Path, relative_path: str) -> Path:
    if ".." in Path(relative_path).parts:
        raise PathValidationError(f"Relative path must not contain '..': {relative_path}")
    candidate = (project_root / relative_path).resolve()
    root = project_root.resolve()
    if root not in candidate.parents and candidate != root:
        raise PathValidationError(f"Path escapes project root: {relative_path}")
    return candidate
