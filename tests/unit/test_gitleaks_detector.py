from unittest.mock import patch

from backend.core.context import ProjectConfig, ScanContext
from backend.detectors.gitleaks import GitleaksDetector


def test_gitleaks_detector_parses_results(tmp_path, monkeypatch) -> None:
    (tmp_path / ".tools").mkdir()
    gitleaks_bin = tmp_path / ".tools" / "gitleaks.exe"
    gitleaks_bin.write_text("", encoding="utf-8")
    config = ProjectConfig(name="demo", path=str(tmp_path), languages=["python"])
    ctx = ScanContext(
        scan_id="scan-1",
        project_config=config,
        project_root=tmp_path,
        results_dir=tmp_path / "results",
    )
    payload = [
        {
            "RuleID": "generic-api-key",
            "File": "app.py",
            "StartLine": 1,
            "Description": "Generic API Key",
            "Secret": "sk-test-1234567890abcdef",
            "Severity": "high",
        }
    ]

    with patch("backend.detectors.gitleaks.run_command") as mock_run, patch(
        "backend.core.path_validation.get_repo_root", return_value=tmp_path
    ):
        def _fake_run(cmd, cwd=None, timeout=300):
            report_path = cmd[cmd.index("--report-path") + 1]
            __import__("json").dump(payload, open(report_path, "w", encoding="utf-8"))
            class Result:
                stderr = ""
                stdout = ""
            return Result()

        mock_run.side_effect = _fake_run
        findings = GitleaksDetector().run(ctx)

    assert len(findings) == 1
    assert findings[0].source == "gitleaks"
    assert "1234" not in findings[0].evidence or "..." in findings[0].evidence
