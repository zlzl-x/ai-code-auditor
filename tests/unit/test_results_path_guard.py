from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.api.security import validate_results_path


def test_validate_results_path_rejects_traversal(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    project_id = "demo"
    (repo_root / "results" / project_id).mkdir(parents=True)
    evil = repo_root / "results" / "other" / ".." / ".." / "etc" / "passwd"
    with pytest.raises(HTTPException):
        validate_results_path(repo_root, project_id, evil)


def test_validate_results_path_allows_project_results(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    project_id = "demo"
    results_dir = repo_root / "results" / project_id / "2026-01-01"
    results_dir.mkdir(parents=True)
    assert validate_results_path(repo_root, project_id, results_dir) == results_dir.resolve()
