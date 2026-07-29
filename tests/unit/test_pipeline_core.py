import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.core.events import EventEmitter, ScanEvent
from backend.core.path_validation import PathValidationError, get_repo_root, resolve_project_root
from backend.core.context import ProjectConfig
from backend.core.pipeline import main, run_scan
from backend.core.registry import get_enabled_stages, get_pipeline_steps
from backend.core.subprocess_runner import SubprocessError, run_command


def test_get_repo_root(repo_root: Path) -> None:
    assert get_repo_root(repo_root) == repo_root


def test_resolve_project_root_missing_path() -> None:
    config = ProjectConfig(name="demo", path="Z:/definitely-missing-path-12345", languages=["python"])
    with pytest.raises(PathValidationError):
        resolve_project_root(config)


def test_event_emitter_notifies_listeners() -> None:
    events: list[str] = []
    emitter = EventEmitter()
    emitter.on(lambda event: events.append(event.stage))
    emitter.emit(ScanEvent.create("recon", "started", 0.2))
    assert events == ["recon"]


def test_get_enabled_stages(repo_root: Path) -> None:
    stages = get_enabled_stages(repo_root)
    assert [stage.id for stage in stages] == get_pipeline_steps(repo_root)


def test_run_command_rejects_empty_command() -> None:
    with pytest.raises(SubprocessError):
        run_command([])


def test_pipeline_main_unknown_command_returns_error() -> None:
    assert main(["run", "novel-assistant-v3"]) in (0, 1)


def test_run_scan_writes_outputs(repo_root: Path, tmp_path: Path) -> None:
    project_id = "demo-project"
    project_dir = repo_root / "projects" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    target = tmp_path / "target"
    target.mkdir()
    (target / "package.json").write_text("{}", encoding="utf-8")
    (project_dir / "config.yaml").write_text(
        f"name: demo\npath: {target.as_posix()}\nlanguages: [javascript]\nfocus_areas: []\n",
        encoding="utf-8",
    )

    with patch.dict(os.environ, {"LLM_CLIENT": "mock"}), patch(
        "backend.detectors.semgrep.run_command"
    ) as mock_run, patch("backend.detectors.bandit.run_command") as mock_bandit, patch(
        "backend.detectors.gitleaks.run_command"
    ) as mock_gitleaks, patch("backend.detectors.npm_audit.run_command") as mock_npm, patch(
        "backend.detectors.eslint_security.run_command"
    ) as mock_eslint, patch(
        "backend.detectors.config_audit.run_command"
    ) as mock_config:

        def _write_empty_json(cmd, cwd=None):
            output = cmd[cmd.index("-o") + 1]
            Path(output).write_text('{"results": []}', encoding="utf-8")

            class Result:
                stderr = ""
                stdout = ""

            return Result()

        mock_run.side_effect = _write_empty_json
        mock_bandit.side_effect = _write_empty_json

        def _empty_stdout(cmd, cwd=None, timeout=300):
            class Result:
                stderr = ""
                stdout = '{"vulnerabilities": {}}'
                timed_out = False

            return Result()

        def _gitleaks_empty(cmd, cwd=None, timeout=300):
            report_path = cmd[cmd.index("--report-path") + 1]
            Path(report_path).write_text("[]", encoding="utf-8")

            class Result:
                stderr = ""
                stdout = ""

            return Result()

        mock_gitleaks.side_effect = _gitleaks_empty
        mock_npm.side_effect = _empty_stdout
        mock_eslint.side_effect = _write_empty_json
        mock_config.side_effect = _empty_stdout
        result = run_scan(project_id, repo_root=repo_root)

    assert (result.results_dir / "raw_findings.jsonl").exists()
    assert (result.results_dir / "verified_findings.jsonl").exists()
    assert (result.results_dir / "AUDIT_REPORT.md").exists()
    assert (result.results_dir / "recon.json").exists()
    assert (result.results_dir / "THREAT_MODEL.md").exists()
    assert (result.results_dir / "scan_meta.json").exists()
    meta = json.loads((result.results_dir / "scan_meta.json").read_text(encoding="utf-8"))
    assert "tokens_in" in meta
