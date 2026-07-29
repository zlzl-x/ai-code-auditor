from pathlib import Path
from unittest.mock import patch

from backend.core.context import ProjectConfig, ScanContext
from backend.sandbox.runner import SandboxRunner


def test_create_snapshot_from_file(tmp_path: Path) -> None:
    source = tmp_path / "demo.py"
    source.write_text("print('x')\n", encoding="utf-8")
    runner = SandboxRunner()
    snapshot = runner.create_snapshot(source)
    assert (snapshot / "demo.py").is_file()


def test_create_snapshot_from_directory(tmp_path: Path) -> None:
    nested = tmp_path / "pkg"
    nested.mkdir()
    (nested / "mod.py").write_text("pass\n", encoding="utf-8")
    runner = SandboxRunner()
    snapshot = runner.create_snapshot(nested)
    assert (snapshot / "mod.py").is_file()


def test_cleanup_invokes_docker_rm() -> None:
    captured: dict = {}

    def _fake_run(cmd, timeout=300, cwd=None):
        captured["cmd"] = cmd
        from backend.core.subprocess_runner import SubprocessResult

        return SubprocessResult(cmd, 0, "", "")

    with patch("backend.sandbox.runner.run_command", side_effect=_fake_run):
        SandboxRunner().cleanup("auditor-sandbox-deadbeef")
    assert captured["cmd"][:3] == ["docker", "rm", "-f"]
