import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from backend.core.context import ProjectConfig, ScanContext
from backend.core.pipeline import run_scan, write_outputs
from backend.stages.find_rules import FindRulesStage


def test_pipeline_full_quick_mode_outputs(tmp_path: Path, repo_root: Path) -> None:
    project_id = "phase2-demo"
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
        result = run_scan(project_id, mode="quick", repo_root=repo_root)

    expected = [
        "recon.json",
        "THREAT_MODEL.md",
        "raw_findings.jsonl",
        "verified_findings.jsonl",
        "TRIAGE.json",
        "AUDIT_REPORT.md",
        "scan_meta.json",
    ]
    for name in expected:
        assert (result.results_dir / name).exists(), f"missing {name}"

    meta = json.loads((result.results_dir / "scan_meta.json").read_text(encoding="utf-8"))
    assert "tokens_in" in meta
    assert "tokens_out" in meta
    assert meta["mode"] == "quick"


def test_find_rules_stage_integration(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    ctx = ScanContext(
        scan_id="scan-1",
        project_config=ProjectConfig(name="demo", path=str(project_root), languages=["javascript"]),
        project_root=project_root,
        results_dir=tmp_path / "results",
    )
    with patch("backend.stages.find_rules.get_enabled_detectors") as mock_detectors:
        class FakeDetector:
            id = "semgrep"

            def run(self, inner_ctx):
                from backend.core.context import Finding, Severity

                return [
                    Finding(
                        scan_id="scan-1",
                        project="demo",
                        severity=Severity.HIGH,
                        source="semgrep",
                        rule_id="spawn-shell-true",
                        file="main.js",
                        line=1,
                        message="shell",
                    )
                ]

        mock_detectors.return_value = [FakeDetector()]
        ctx = FindRulesStage().run(ctx)

    write_outputs(ctx, datetime.now(timezone.utc))
    lines = (ctx.results_dir / "raw_findings.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
