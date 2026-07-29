from unittest.mock import patch

import pytest


def test_health(api_env) -> None:
    client, _repo = api_env
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


def test_list_projects(api_env) -> None:
    client, _repo = api_env
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert any(item["id"] == "demo" for item in response.json()["data"])


def test_settings_no_api_key_leak(api_env, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _repo = api_env
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-deepseek-key")
    response = client.get("/api/settings")
    assert "secret-deepseek-key" not in response.text
    assert response.json()["data"]["deepseek_api_key_configured"] is True
    assert response.json()["data"]["llm_provider"] == "deepseek"


def test_patch_finding_triage(api_env) -> None:
    from backend.core.context import Finding, Severity

    client, repo = api_env
    repo.create_scan("scan-1", "demo", "quick")
    finding = Finding(
        scan_id="scan-1",
        project="demo",
        severity=Severity.HIGH,
        source="semgrep",
        rule_id="test.rule",
        file="a.py",
        line=1,
        message="<script>alert(1)</script>",
    )
    repo.import_findings("scan-1", [finding])
    response = client.patch(
        f"/api/findings/{finding.id}",
        json={"status": "false_positive"},
        headers={"Origin": "http://127.0.0.1:8787"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "false_positive"


def test_start_scan(api_env) -> None:
    client, repo = api_env
    with patch("backend.api.routes.execute_scan") as mock_exec:
        response = client.post(
            "/api/scans",
            json={"project_id": "demo", "mode": "quick"},
            headers={"Origin": "http://127.0.0.1:8787"},
        )
        assert response.status_code == 200
        scan_id = response.json()["data"]["id"]
        assert repo.get_scan(scan_id)["status"] == "pending"
        assert mock_exec.called


def test_stats_and_modules(api_env) -> None:
    client, _repo = api_env
    stats = client.get("/api/stats")
    assert stats.status_code == 200
    modules = client.get("/api/modules")
    assert modules.status_code == 200
    assert "pipeline" in modules.json()["data"]


def test_rules_and_knowledge(api_env) -> None:
    client, _repo = api_env
    rules = client.get("/api/rules")
    assert rules.status_code == 200
    feed = client.get("/api/knowledge/feed?limit=3")
    assert feed.status_code == 200
    backlog = client.get("/api/knowledge/backlog")
    assert backlog.status_code == 200


def test_get_scan(api_env) -> None:
    client, repo = api_env
    scan = repo.create_scan("scan-get", "demo", "quick")
    response = client.get(f"/api/scans/{scan['id']}")
    assert response.status_code == 200
    assert response.json()["data"]["id"] == scan["id"]


def test_settings_patch(api_env) -> None:
    client, _repo = api_env
    response = client.patch(
        "/api/settings",
        json={"report_mode": "block"},
        headers={"Origin": "http://127.0.0.1:8787"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["report_mode"] == "block"


def test_rules_reload(api_env) -> None:
    client, _repo = api_env
    response = client.post("/api/rules/reload", headers={"Origin": "http://127.0.0.1:8787"})
    assert response.status_code == 200
