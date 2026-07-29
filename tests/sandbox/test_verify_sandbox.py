from backend.core.context import Finding, ProjectConfig, ScanContext, Severity
from backend.sandbox.runner import SandboxResult
from backend.stages.verify_sandbox import VerifySandboxStage


def _ctx(*, enable_sandbox: bool = False) -> ScanContext:
    finding = Finding(
        scan_id="scan-1",
        project="demo",
        severity=Severity.HIGH,
        source="semgrep",
        rule_id="python.lang.security.audit.spawn-shell-true",
        file="app.py",
        line=1,
        message="subprocess shell true",
        verified=True,
        cwe="CWE-78",
    )
    return ScanContext(
        scan_id="scan-1",
        project_config=ProjectConfig(name="demo", path=".", languages=["python"]),
        project_root=__import__("pathlib").Path("."),
        results_dir=__import__("pathlib").Path("."),
        verified_findings=[finding],
        enable_sandbox=enable_sandbox,
    )


def test_verify_sandbox_skipped_by_default() -> None:
    ctx = VerifySandboxStage().run(_ctx(enable_sandbox=False))
    assert ctx.sandbox_results == {}


def test_verify_sandbox_records_error_without_docker(monkeypatch) -> None:
    monkeypatch.setattr("backend.stages.verify_sandbox.SandboxRunner.is_available", lambda: False)
    ctx = VerifySandboxStage().run(_ctx(enable_sandbox=True))
    assert any("docker not available" in error for error in ctx.errors)


def test_verify_sandbox_runs_poc_for_verifiable_finding(tmp_path, monkeypatch) -> None:
    target = tmp_path / "app.py"
    target.write_text("import subprocess\n", encoding="utf-8")
    finding = Finding(
        scan_id="scan-1",
        project="demo",
        severity=Severity.HIGH,
        source="semgrep",
        rule_id="python.lang.security.audit.spawn-shell-true",
        file=str(target),
        line=1,
        message="subprocess shell true",
        verified=True,
        cwe="CWE-78",
    )
    ctx = ScanContext(
        scan_id="scan-1",
        project_config=ProjectConfig(name="demo", path=str(tmp_path), languages=["python"]),
        project_root=tmp_path,
        results_dir=tmp_path / "results",
        verified_findings=[finding],
        enable_sandbox=True,
    )
    monkeypatch.setattr("backend.stages.verify_sandbox.SandboxRunner.is_available", lambda: True)
    monkeypatch.setattr(
        "backend.stages.verify_sandbox.SandboxRunner.create_snapshot",
        lambda self, source: tmp_path / "snap",
    )
    monkeypatch.setattr(
        "backend.stages.verify_sandbox.SandboxRunner.run_poc",
        lambda self, command, snapshot: SandboxResult(0, "ok", "", False, "cid"),
    )
    monkeypatch.setattr("backend.stages.verify_sandbox.SandboxRunner.cleanup", lambda self, cid: None)

    ctx = VerifySandboxStage().run(ctx)
    assert ctx.sandbox_results["attempted"] == 1
    assert ctx.verified_findings[0].sandbox_note == "poc_confirmed"
