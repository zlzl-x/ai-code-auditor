from unittest.mock import patch

from backend.core.context import ProjectConfig, ScanContext
from backend.detectors.config_audit import ConfigAuditDetector


def test_config_audit_detector_parses_agentshield_json(tmp_path, monkeypatch) -> None:
    cursor_dir = tmp_path / ".cursor"
    cursor_dir.mkdir()
    config = ProjectConfig(name="demo", path=str(tmp_path), languages=[])
    ctx = ScanContext(
        scan_id="scan-1",
        project_config=config,
        project_root=tmp_path,
        results_dir=tmp_path / "results",
    )
    payload = {
        "findings": [
            {
                "ruleId": "agentshield.skill.unsafe",
                "severity": "high",
                "message": "Unsafe skill pattern",
                "location": {"file": ".cursor/skills/demo/SKILL.md", "line": 1},
            }
        ]
    }

    with patch("backend.detectors.config_audit.run_command") as mock_run, patch(
        "backend.detectors.config_audit.shutil.which", return_value="/usr/bin/npx"
    ):
        class Result:
            stdout = __import__("json").dumps(payload)
            stderr = ""

        mock_run.return_value = Result()
        findings = ConfigAuditDetector().run(ctx)

    assert len(findings) == 1
    assert findings[0].source == "agentshield"


def test_config_audit_skips_without_agent_dirs(tmp_path) -> None:
    config = ProjectConfig(name="demo", path=str(tmp_path), languages=[])
    ctx = ScanContext(
        scan_id="scan-1",
        project_config=config,
        project_root=tmp_path,
        results_dir=tmp_path / "results",
    )
    assert ConfigAuditDetector().run(ctx) == []
