from unittest.mock import patch

from backend.core.context import ProjectConfig, ScanContext
from backend.detectors.bandit import BanditDetector


def test_bandit_detector_parses_results(tmp_path) -> None:
    skills = tmp_path / ".cursor" / "skills"
    skills.mkdir(parents=True)
    (skills / "demo.py").write_text("password = 'secret'\n", encoding="utf-8")
    config = ProjectConfig(name="demo", path=str(tmp_path), languages=["python"])
    ctx = ScanContext(
        scan_id="scan-1",
        project_config=config,
        project_root=tmp_path,
        results_dir=tmp_path / "results",
    )
    payload = {
        "results": [
            {
                "test_id": "B105",
                "filename": str(skills / "demo.py"),
                "line_number": 1,
                "issue_text": "hardcoded password",
                "issue_severity": "LOW",
                "code": "password = 'secret'",
            }
        ]
    }

    with patch("backend.detectors.bandit.run_command") as mock_run:
        output_file = tmp_path / "bandit.json"
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
        findings = BanditDetector().run(ctx)

    assert len(findings) == 1
    assert findings[0].source == "bandit"
