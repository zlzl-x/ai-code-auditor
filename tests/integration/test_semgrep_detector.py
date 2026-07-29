from unittest.mock import patch

from backend.core.context import ProjectConfig, ScanContext
from backend.detectors.semgrep import SemgrepDetector


def test_semgrep_detector_parses_results(tmp_path) -> None:
    project_root = tmp_path / "app"
    project_root.mkdir()
    (project_root / "main.js").write_text("console.log('x')", encoding="utf-8")
    config = ProjectConfig(
        name="demo",
        path=str(project_root),
        languages=["javascript"],
        focus_areas=[],
    )
    ctx = ScanContext(
        scan_id="scan-1",
        project_config=config,
        project_root=project_root,
        results_dir=tmp_path / "results",
    )
    payload = {
        "results": [
            {
                "check_id": "javascript.lang.security.audit.spawn-shell-true.spawn-shell-true",
                "path": str(project_root / "main.js"),
                "start": {"line": 1},
                "extra": {
                    "message": "spawn shell true",
                    "severity": "ERROR",
                    "lines": "spawn(..., {shell: true})",
                    "metadata": {},
                },
            }
        ]
    }

    with patch("backend.detectors.semgrep.run_command") as mock_run:
        output_file = tmp_path / "semgrep.json"
        output_file.write_text(__import__("json").dumps(payload), encoding="utf-8")

        def _fake_run(cmd, cwd=None):
            for index, part in enumerate(cmd):
                if part == "-o":
                    target = cmd[index + 1]
                    output_file.replace(target)
            class Result:
                stderr = ""
                stdout = ""
            return Result()

        mock_run.side_effect = _fake_run
        findings = SemgrepDetector().run(ctx)

    assert len(findings) == 1
    assert "spawn-shell" in findings[0].rule_id
