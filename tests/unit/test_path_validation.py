from pathlib import Path

import pytest

from backend.core.context import ProjectConfig
from backend.core.path_validation import (
    PathValidationError,
    ensure_child_path,
    load_project_config,
    resolve_project_root,
)


def test_load_project_config(repo_root: Path) -> None:
    config = load_project_config("novel-assistant-v3", repo_root)
    assert config.name == "novel-assistant-v3"
    assert config.languages == ["typescript", "javascript"]


def test_resolve_project_root_rejects_traversal() -> None:
    config = ProjectConfig(name="demo", path="../outside", languages=["python"])
    with pytest.raises(PathValidationError):
        resolve_project_root(config)


def test_ensure_child_path_blocks_escape(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    with pytest.raises(PathValidationError):
        ensure_child_path(project_root, "../escape")
