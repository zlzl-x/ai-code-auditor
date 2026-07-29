from backend.models.repository import AppRepository


def test_repository_scan_lifecycle(tmp_path) -> None:
    db_path = tmp_path / "app.db"
    repo_root = tmp_path / "repo"
    (repo_root / "projects" / "demo").mkdir(parents=True)
    (repo_root / "projects" / "demo" / "config.yaml").write_text(
        "name: demo\npath: .\nlanguages: [python]\n",
        encoding="utf-8",
    )
    repo = AppRepository(db_path=db_path, repo_root=repo_root)
    projects = repo.list_projects()
    assert any(p["id"] == "demo" for p in projects)
    scan = repo.create_scan("scan-1", "demo", "quick")
    repo.update_scan("scan-1", status="completed", results_dir="/tmp/results")
    updated = repo.get_scan("scan-1")
    assert updated["status"] == "completed"
    assert repo.scans_today() >= 1
