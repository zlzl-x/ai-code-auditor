import json
from pathlib import Path
from unittest.mock import patch

from backend.cli import main


def test_cli_scan_sarif_output(tmp_path, monkeypatch) -> None:
    project_id = "cli-demo"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)
    target = tmp_path / "target"
    target.mkdir()
    (target / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (project_dir / "config.yaml").write_text(
        f"name: demo\npath: {target.as_posix()}\nlanguages: [python]\n",
        encoding="utf-8",
    )
    (tmp_path / "modules.yaml").write_text(
        "detectors: [semgrep, bandit]\npipeline: [recon, find_rules, verify_llm, triage, report_md]\nreporters: [markdown]\n",
        encoding="utf-8",
    )
    output = tmp_path / "out.sarif"
    monkeypatch.setenv("LLM_CLIENT", "mock")

    with patch("backend.cli.get_repo_root", return_value=tmp_path), patch(
        "backend.core.pipeline.get_repo_root", return_value=tmp_path
    ), patch("backend.core.path_validation.get_repo_root", return_value=tmp_path), patch(
        "backend.detectors.semgrep.run_command"
    ) as mock_run, patch("backend.detectors.bandit.run_command") as mock_bandit, patch(
        "backend.detectors.gitleaks.run_command"
    ), patch("backend.detectors.npm_audit.run_command"), patch(
        "backend.detectors.eslint_security.run_command"
    ), patch(
        "backend.detectors.config_audit.run_command"
    ):

        def _write_empty_json(cmd, cwd=None, timeout=300):
            if "-o" in cmd:
                out = cmd[cmd.index("-o") + 1]
                Path(out).write_text('{"results": []}', encoding="utf-8")
            class Result:
                stderr = ""
                stdout = ""
                timed_out = False
            return Result()

        mock_run.side_effect = _write_empty_json
        mock_bandit.side_effect = _write_empty_json
        exit_code = main(
            [
                "scan",
                "--project",
                project_id,
                "--format",
                "sarif",
                "-o",
                str(output),
                "--report-mode",
                "report_only",
            ]
        )

    assert exit_code == 0
    assert output.is_file()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["version"] == "2.1.0"
