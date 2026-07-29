import pytest

from backend.core.rules_loader import scan_rules


def test_scan_rules_counts_ids(repo_root) -> None:
    info = scan_rules(repo_root)
    assert info["rule_count"] >= 5
    assert any(rule_id.startswith("python.") for rule_id in info["rule_ids"])


def test_rules_reload_rejects_path_traversal(api_env) -> None:
    client, _repo = api_env
    response = client.post(
        "/api/rules/reload?path=../backend/main.py",
        headers={"Origin": "http://127.0.0.1:8787"},
    )
    assert response.status_code == 400


def test_rules_reload_returns_rule_metadata(api_env, tmp_path, monkeypatch) -> None:
    client, _repo = api_env
    rules_dir = tmp_path / "rules" / "demo"
    rules_dir.mkdir(parents=True)
    (rules_dir / "sample.yaml").write_text(
        "rules:\n  - id: demo.rule\n    message: test\n    severity: INFO\n",
        encoding="utf-8",
    )
    response = client.post("/api/rules/reload", headers={"Origin": "http://127.0.0.1:8787"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert "gitleaks" in data["detectors"]
    assert data["rule_count"] >= 1
