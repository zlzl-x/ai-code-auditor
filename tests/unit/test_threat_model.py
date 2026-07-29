from backend.core.context import ProjectConfig, ScanContext
from backend.stages.recon import ReconStage


def test_recon_generates_threat_model(tmp_path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "app.py").write_text("print('hi')\n", encoding="utf-8")
    config = ProjectConfig(
        name="demo",
        path=str(tmp_path),
        languages=["python"],
        focus_areas=[],
    )
    ctx = ScanContext(
        scan_id="scan-1",
        project_config=config,
        project_root=tmp_path,
        results_dir=tmp_path / "results",
    )
    ctx = ReconStage().run(ctx)
    assert ctx.threat_model_md
    assert "Threat Model" in ctx.threat_model_md
    assert "package.json" in ctx.threat_model_md
