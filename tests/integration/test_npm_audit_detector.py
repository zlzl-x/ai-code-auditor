from unittest.mock import patch

from backend.core.context import ProjectConfig, ScanContext
from backend.detectors.npm_audit import NpmAuditDetector


def test_npm_audit_detector_parses_results(tmp_path, monkeypatch) -> None:
    (tmp_path / "package.json").write_text('{"name":"demo"}', encoding="utf-8")
    config = ProjectConfig(name="demo", path=str(tmp_path), languages=["javascript"])
    ctx = ScanContext(
        scan_id="scan-1",
        project_config=config,
        project_root=tmp_path,
        results_dir=tmp_path / "results",
    )
    payload = {
        "vulnerabilities": {
            "lodash": {
                "severity": "high",
                "range": "<4.17.21",
                "via": [{"title": "Prototype Pollution"}],
            }
        }
    }

    with patch("backend.detectors.npm_audit.run_command") as mock_run:
        class Result:
            stdout = __import__("json").dumps(payload)
            stderr = ""
            timed_out = False

        mock_run.return_value = Result()
        findings = NpmAuditDetector().run(ctx)

    assert len(findings) == 1
    assert findings[0].source == "npm_audit"
    assert findings[0].message == "Prototype Pollution"
