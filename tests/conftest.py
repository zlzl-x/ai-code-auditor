from __future__ import annotations

import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.database import init_db
from backend.models.repository import AppRepository

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def canary_project_path() -> str:
    return os.environ.get("CANARY_PROJECT_PATH", r"G:\小说创作助手-v3")


@pytest.fixture
def api_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "app.db"
    init_db(db_path)
    (tmp_path / "projects").mkdir()
    (tmp_path / "projects" / "demo").mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (target / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "projects" / "demo" / "config.yaml").write_text(
        f"name: demo\npath: {target.as_posix()}\nlanguages: [python]\n",
        encoding="utf-8",
    )
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "index.html").write_text("<html></html>", encoding="utf-8")
    shutil.copy(REPO_ROOT / "modules.yaml", tmp_path / "modules.yaml")
    monkeypatch.setenv("LLM_CLIENT", "mock")
    repo = AppRepository(db_path=db_path, repo_root=tmp_path)

    with patch("backend.core.path_validation.get_repo_root", return_value=tmp_path), patch(
        "backend.api.routes.get_repo_root", return_value=tmp_path
    ), patch("backend.api.scan_service.get_repo_root", return_value=tmp_path), patch(
        "backend.models.repository.default_db_path", return_value=db_path
    ), patch("backend.api.routes.get_repo", return_value=repo), patch(
        "backend.api.routes.AppRepository", return_value=repo
    ), patch("backend.api.scan_service.AppRepository", return_value=repo):
        yield TestClient(app), repo