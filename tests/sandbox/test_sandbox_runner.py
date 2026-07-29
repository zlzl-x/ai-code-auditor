from pathlib import Path
from unittest.mock import patch

from backend.core.subprocess_runner import SubprocessResult
from backend.sandbox.runner import SandboxRunner, sanitize_log


def test_sanitize_log_redacts_paths() -> None:
    text = "failed at G:\\secrets\\.env and /home/user/key"
    sanitized = sanitize_log(text)
    assert "G:\\secrets" not in sanitized
    assert "/home/user" not in sanitized


def test_run_poc_uses_network_none(tmp_path: Path) -> None:
    runner = SandboxRunner()
    snapshot = runner.create_snapshot(tmp_path)
    captured: dict = {}

    def _fake_run(cmd, timeout=300, cwd=None):
        captured["cmd"] = cmd
        return SubprocessResult(cmd, 0, "ok", "", timed_out=False)

    with patch("backend.sandbox.runner.run_command", side_effect=_fake_run), patch.object(
        SandboxRunner, "is_available", return_value=True
    ):
        result = runner.run_poc(["python", "-c", "print('poc')"], snapshot)

    assert result.exit_code == 0
    assert "--network" in captured["cmd"]
    assert "none" in captured["cmd"]
    assert ":ro" in "".join(captured["cmd"])


def test_is_available_checks_docker_info() -> None:
    with patch("backend.sandbox.runner.shutil.which", return_value="/usr/bin/docker"), patch(
        "backend.sandbox.runner.run_command",
        return_value=SubprocessResult(["docker", "info"], 0, "", ""),
    ):
        assert SandboxRunner.is_available() is True
