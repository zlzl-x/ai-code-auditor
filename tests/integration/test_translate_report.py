from pathlib import Path
from unittest.mock import patch

from backend.core.pipeline import run_scan
from backend.stages.report_md import ReportMdStage


def test_run_scan_lang_zh_skips_translation_with_mock(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LLM_CLIENT", "mock")
    project_id = "translate-demo"
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
        "detectors: []\npipeline: [report_md]\nreporters: [markdown]\n",
        encoding="utf-8",
    )
    results_dir = tmp_path / "results" / project_id / "scan-1"
    results_dir.mkdir(parents=True)

    with patch("backend.core.pipeline.get_repo_root", return_value=tmp_path), patch(
        "backend.core.path_validation.get_repo_root", return_value=tmp_path
    ), patch("backend.core.pipeline.get_enabled_stages", return_value=[ReportMdStage()]), patch(
        "backend.core.pipeline.load_modules_config",
        return_value={"detectors": [], "pipeline": ["report_md"], "reporters": ["markdown"], "llm": {}},
    ):
        result = run_scan(
            project_id,
            repo_root=tmp_path,
            results_dir=results_dir,
            report_lang="zh",
        )

    assert result.ctx.report_lang == "zh"
    assert (results_dir / "AUDIT_REPORT.md").is_file()
    assert not (results_dir / "AUDIT_REPORT.zh.md").exists()
    assert any("translate_report: skipped" in error for error in result.ctx.errors)
    meta = __import__("json").loads((results_dir / "scan_meta.json").read_text(encoding="utf-8"))
    assert meta["report_lang"] == "zh"
